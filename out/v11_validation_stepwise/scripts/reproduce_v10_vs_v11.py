#!/usr/bin/env python3
"""Reproducible V10 vs V11 comparison — deterministic, no randomness in backtest.

Outputs:
  - summary_full_backtest.csv   (V10/V11/Delta × 3 scenarios)
  - paired_bootstrap.csv        (Sharpe bootstrap, seed=42, 5000 resamples)
  - stdout log (redirect to repro_run.log)

PASS criteria: running twice produces bitwise identical CSV output.
Backtest engine is fully deterministic (no random elements).
Bootstrap uses fixed seed=42.
"""

import csv
import hashlib
import json
import sys
from io import StringIO
from pathlib import Path

import numpy as np

# Ensure deterministic numpy
np.seterr(all="ignore")

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS
from v10.research.bootstrap import calc_sharpe
from v10.research.objective import compute_objective
from v10.strategies.v8_apex import V8ApexConfig, V8ApexStrategy
from v10.strategies.v11_hybrid import V11HybridConfig, V11HybridStrategy

# ── Constants ──────────────────────────────────────────────────────────
DATA_PATH = "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
START = "2019-01-01"
END = "2026-02-20"
WARMUP_DAYS = 365
BOOTSTRAP_SEED = 42
BOOTSTRAP_N = 5000
BOOTSTRAP_BLOCK = 20

OUTDIR = Path("out_v11_validation_stepwise")


def make_v10():
    return V8ApexStrategy(V8ApexConfig())


def make_v11_wfo_opt():
    cfg = V11HybridConfig()
    cfg.enable_cycle_phase = True
    cfg.cycle_early_aggression = 1.0
    cfg.cycle_early_trail_mult = 3.5
    cfg.cycle_late_aggression = 0.95
    cfg.cycle_late_trail_mult = 2.8
    cfg.cycle_late_max_exposure = 0.90
    return V11HybridStrategy(cfg)


def run_backtest(strategy, scenario_name):
    cost = SCENARIOS[scenario_name]
    feed = DataFeed(DATA_PATH, start=START, end=END, warmup_days=WARMUP_DAYS)
    engine = BacktestEngine(
        feed=feed, strategy=strategy, cost=cost,
        initial_cash=10_000.0, warmup_mode="no_trade",
    )
    return engine.run()


def paired_bootstrap_sharpe(equity_a, equity_b, n=BOOTSTRAP_N, block=BOOTSTRAP_BLOCK, seed=BOOTSTRAP_SEED):
    navs_a = np.array([e.nav_mid for e in equity_a], dtype=np.float64)
    navs_b = np.array([e.nav_mid for e in equity_b], dtype=np.float64)
    ln = min(len(navs_a), len(navs_b))
    ret_a = np.diff(navs_a[:ln]) / navs_a[:ln-1]
    ret_b = np.diff(navs_b[:ln]) / navs_b[:ln-1]

    obs_a = calc_sharpe(ret_a)
    obs_b = calc_sharpe(ret_b)
    obs_delta = obs_a - obs_b

    rng = np.random.default_rng(seed)
    m = len(ret_a)
    n_blocks = int(np.ceil(m / block))
    deltas = np.empty(n, dtype=np.float64)
    for i in range(n):
        starts = rng.integers(0, m, size=n_blocks)
        idx = np.concatenate([np.arange(s, s + block) % m for s in starts])[:m]
        deltas[i] = calc_sharpe(ret_a[idx]) - calc_sharpe(ret_b[idx])

    return {
        "sharpe_v11": obs_a,
        "sharpe_v10": obs_b,
        "delta": obs_delta,
        "delta_mean": float(deltas.mean()),
        "delta_std": float(deltas.std(ddof=1)),
        "ci_lower": float(np.percentile(deltas, 2.5)),
        "ci_upper": float(np.percentile(deltas, 97.5)),
        "p_v11_better": float((deltas > 0).mean()),
        "n_bootstrap": n,
        "block_size": block,
        "seed": seed,
    }


def main():
    print("=" * 70)
    print("  REPRODUCIBLE V10 vs V11 COMPARISON")
    print("=" * 70)
    print(f"  Data: {DATA_PATH}")
    print(f"  Range: {START} → {END}, warmup={WARMUP_DAYS}d")
    print(f"  Bootstrap: n={BOOTSTRAP_N}, block={BOOTSTRAP_BLOCK}, seed={BOOTSTRAP_SEED}")
    print(f"  Baseline: V8ApexConfig() defaults")
    print(f"  Candidate: V11HybridConfig WFO-optimal (0.95/2.8/0.90)")
    print()

    # ── Part 1: Full backtest ──────────────────────────────────────────
    rows = []  # for CSV
    equities = {}

    for scenario_name in ["smart", "base", "harsh"]:
        cost_cfg = SCENARIOS[scenario_name]
        rt_bps = cost_cfg.round_trip_bps
        print(f"  [{scenario_name}] round_trip={rt_bps:.1f} bps")

        res_v10 = run_backtest(make_v10(), scenario_name)
        res_v11 = run_backtest(make_v11_wfo_opt(), scenario_name)

        equities[scenario_name] = (res_v11.equity, res_v10.equity)

        s10 = res_v10.summary
        s11 = res_v11.summary
        sc10 = compute_objective(s10)
        sc11 = compute_objective(s11)

        for label, s, sc in [("V10", s10, sc10), ("V11_WFO_opt", s11, sc11)]:
            rows.append({
                "strategy": label,
                "scenario": scenario_name,
                "score": f"{sc:.4f}",
                "cagr_pct": f"{s.get('cagr_pct', 0):.4f}",
                "max_dd_pct": f"{s.get('max_drawdown_mid_pct', 0):.4f}",
                "sharpe": f"{s.get('sharpe', 0):.4f}",
                "profit_factor": f"{s.get('profit_factor', 0):.4f}",
                "trades": str(s.get("trades", 0)),
                "final_nav": f"{s.get('final_nav_mid', 0):.2f}",
                "win_rate_pct": f"{s.get('win_rate_pct', 0):.2f}",
            })

        # Delta row
        rows.append({
            "strategy": "DELTA",
            "scenario": scenario_name,
            "score": f"{sc11 - sc10:.4f}",
            "cagr_pct": f"{s11.get('cagr_pct',0) - s10.get('cagr_pct',0):.4f}",
            "max_dd_pct": f"{s11.get('max_drawdown_mid_pct',0) - s10.get('max_drawdown_mid_pct',0):.4f}",
            "sharpe": f"{(s11.get('sharpe') or 0) - (s10.get('sharpe') or 0):.4f}",
            "profit_factor": "",
            "trades": str(s11.get("trades",0) - s10.get("trades",0)),
            "final_nav": f"{s11.get('final_nav_mid',0) - s10.get('final_nav_mid',0):.2f}",
            "win_rate_pct": "",
        })

        print(f"    V10: score={sc10:.4f} CAGR={s10.get('cagr_pct',0):.2f}% "
              f"MDD={s10.get('max_drawdown_mid_pct',0):.2f}% Sharpe={s10.get('sharpe',0):.4f}")
        print(f"    V11: score={sc11:.4f} CAGR={s11.get('cagr_pct',0):.2f}% "
              f"MDD={s11.get('max_drawdown_mid_pct',0):.2f}% Sharpe={s11.get('sharpe',0):.4f}")
        print(f"    Delta: score={sc11-sc10:+.4f}")

    # Write CSV
    csv_path = OUTDIR / "summary_full_backtest.csv"
    fieldnames = ["strategy", "scenario", "score", "cagr_pct", "max_dd_pct",
                  "sharpe", "profit_factor", "trades", "final_nav", "win_rate_pct"]
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"\n  Saved: {csv_path}")

    # ── Part 2: Paired bootstrap ───────────────────────────────────────
    print(f"\n  Paired bootstrap (seed={BOOTSTRAP_SEED}):")
    bs_rows = []
    for scenario_name in ["smart", "base", "harsh"]:
        eq_v11, eq_v10 = equities[scenario_name]
        bs = paired_bootstrap_sharpe(eq_v11, eq_v10)
        bs["scenario"] = scenario_name
        bs_rows.append(bs)
        print(f"    [{scenario_name}] delta={bs['delta']:+.4f} "
              f"CI=[{bs['ci_lower']:+.4f}, {bs['ci_upper']:+.4f}] "
              f"P(V11>V10)={bs['p_v11_better']:.4f} seed={bs['seed']}")

    bs_csv_path = OUTDIR / "paired_bootstrap.csv"
    bs_fields = ["scenario", "sharpe_v11", "sharpe_v10", "delta", "delta_mean",
                 "delta_std", "ci_lower", "ci_upper", "p_v11_better",
                 "n_bootstrap", "block_size", "seed"]
    with open(bs_csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=bs_fields)
        w.writeheader()
        w.writerows(bs_rows)
    print(f"  Saved: {bs_csv_path}")

    # ── Part 3: File hash for reproducibility check ────────────────────
    for fpath in [csv_path, bs_csv_path]:
        h = hashlib.sha256(fpath.read_bytes()).hexdigest()
        print(f"\n  SHA256({fpath.name}): {h}")

    print("\n" + "=" * 70)
    print("  DONE. Run twice and compare SHA256 hashes for PASS/FAIL.")
    print("=" * 70)


if __name__ == "__main__":
    main()
