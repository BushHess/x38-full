"""V11 extended WFO + bootstrap validation.

Runs:
1. Fixed-param WFO: V11 winner, V10 baseline, WFO-optimal — all 10 windows
2. Enhanced paired bootstrap: 5000 resamples × 3 block sizes × 3 scenarios
3. Per-window OOS comparison table
"""

import json
import math
from pathlib import Path

import numpy as np

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS, EquitySnap
from v10.research.bootstrap import calc_sharpe, calc_cagr, calc_max_drawdown
from v10.research.objective import compute_objective
from v10.research.wfo import generate_windows, WFOWindowSpec
from v10.strategies.v8_apex import V8ApexConfig, V8ApexStrategy
from v10.strategies.v11_hybrid import V11HybridConfig, V11HybridStrategy


DATA_PATH = "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
START = "2019-01-01"
END = "2026-02-20"
WARMUP = 365


def make_v11_winner() -> V11HybridStrategy:
    cfg = V11HybridConfig()
    cfg.enable_cycle_phase = True
    cfg.cycle_early_aggression = 1.0
    cfg.cycle_early_trail_mult = 3.5
    cfg.cycle_late_aggression = 0.90
    cfg.cycle_late_trail_mult = 3.0
    cfg.cycle_late_max_exposure = 0.90
    return V11HybridStrategy(cfg)


def make_v11_wfo_optimal() -> V11HybridStrategy:
    cfg = V11HybridConfig()
    cfg.enable_cycle_phase = True
    cfg.cycle_early_aggression = 1.0
    cfg.cycle_early_trail_mult = 3.5
    cfg.cycle_late_aggression = 0.95
    cfg.cycle_late_trail_mult = 2.8
    cfg.cycle_late_max_exposure = 0.90
    return V11HybridStrategy(cfg)


def backtest_window(strategy_factory, window: WFOWindowSpec, scenario: str = "base"):
    """Run a single backtest on a WFO window."""
    cost = SCENARIOS[scenario]
    strategy = strategy_factory()
    feed = DataFeed(DATA_PATH, start=window.test_start, end=window.test_end,
                    warmup_days=WARMUP)
    engine = BacktestEngine(feed=feed, strategy=strategy, cost=cost,
                            initial_cash=10_000.0)
    result = engine.run()
    s = result.summary
    return {
        "return_pct": s.get("total_return_pct", 0.0),
        "cagr_pct": s.get("cagr_pct", 0.0),
        "mdd_pct": s.get("max_drawdown_mid_pct", 0.0),
        "sharpe": s.get("sharpe"),
        "trades": s.get("trades", 0),
        "score": compute_objective(s),
        "equity": result.equity,
    }


def paired_bootstrap_enhanced(
    equity_a: list[EquitySnap],
    equity_b: list[EquitySnap],
    n_bootstrap: int = 5000,
    block_sizes: list[int] = None,
    seed: int = 42,
) -> list[dict]:
    """Paired block bootstrap with multiple block sizes for robustness."""
    if block_sizes is None:
        block_sizes = [10, 20, 40]

    navs_a = np.array([e.nav_mid for e in equity_a], dtype=np.float64)
    navs_b = np.array([e.nav_mid for e in equity_b], dtype=np.float64)
    n = min(len(navs_a), len(navs_b))
    ret_a = np.diff(navs_a[:n]) / navs_a[:n-1]
    ret_b = np.diff(navs_b[:n]) / navs_b[:n-1]

    observed_a = calc_sharpe(ret_a)
    observed_b = calc_sharpe(ret_b)
    observed_delta = observed_a - observed_b

    results = []
    for bs in block_sizes:
        rng = np.random.default_rng(seed)
        m = len(ret_a)
        n_blocks = int(np.ceil(m / bs))
        deltas = np.empty(n_bootstrap, dtype=np.float64)

        for i in range(n_bootstrap):
            starts = rng.integers(0, m, size=n_blocks)
            indices = np.concatenate([np.arange(s, s + bs) % m for s in starts])[:m]
            sa = calc_sharpe(ret_a[indices])
            sb = calc_sharpe(ret_b[indices])
            deltas[i] = sa - sb

        results.append({
            "block_size": bs,
            "n_bootstrap": n_bootstrap,
            "sharpe_a": round(observed_a, 4),
            "sharpe_b": round(observed_b, 4),
            "delta_observed": round(observed_delta, 4),
            "delta_mean": round(float(deltas.mean()), 4),
            "delta_std": round(float(deltas.std(ddof=1)), 4),
            "ci_lower": round(float(np.percentile(deltas, 2.5)), 4),
            "ci_upper": round(float(np.percentile(deltas, 97.5)), 4),
            "p_a_better": round(float((deltas > 0).mean()), 4),
        })

    return results


def main():
    outdir = Path("out/v11_wfo_extended")
    outdir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("  V11 EXTENDED WFO + BOOTSTRAP VALIDATION")
    print("=" * 70)

    # Generate windows (same as previous WFO)
    windows = generate_windows(START, END, train_months=24, test_months=6, slide_months=6)
    print(f"\n  {len(windows)} OOS windows generated")

    strategies = {
        "v10_baseline": lambda: V8ApexStrategy(V8ApexConfig()),
        "v11_winner": make_v11_winner,
        "v11_wfo_opt": make_v11_wfo_optimal,
    }

    # ====================================================================
    # PART 1: Fixed-param WFO — all strategies × all windows
    # ====================================================================
    print("\n" + "=" * 70)
    print("  PART 1: FIXED-PARAM WFO (all 10 OOS windows, base scenario)")
    print("=" * 70)

    wfo_results = {}
    for strat_name, factory in strategies.items():
        wfo_results[strat_name] = []
        for w in windows:
            print(f"  {strat_name} window {w.window_id}: "
                  f"{w.test_start} → {w.test_end} ...", end=" ", flush=True)
            r = backtest_window(factory, w, scenario="base")
            r_no_eq = {k: v for k, v in r.items() if k != "equity"}
            wfo_results[strat_name].append({
                "window_id": w.window_id,
                "test_start": w.test_start,
                "test_end": w.test_end,
                **r_no_eq,
            })
            passed = r["return_pct"] > -5.0 and r["mdd_pct"] < 35.0
            print(f"ret={r['return_pct']:+.1f}% mdd={r['mdd_pct']:.1f}% "
                  f"trades={r['trades']} {'PASS' if passed else 'FAIL'}")

    # Summary table
    print(f"\n  {'Strategy':<16} {'Windows':>7} {'Passed':>6} {'Rate':>6} "
          f"{'Med Ret%':>8} {'Med MDD%':>8} {'Med Score':>9}")
    print("  " + "-" * 75)
    for strat_name in strategies:
        wr = wfo_results[strat_name]
        n_passed = sum(1 for w in wr if w["return_pct"] > -5.0 and w["mdd_pct"] < 35.0)
        rets = sorted([w["return_pct"] for w in wr])
        mdds = sorted([w["mdd_pct"] for w in wr])
        scores = sorted([w["score"] for w in wr])
        med_ret = rets[len(rets)//2]
        med_mdd = mdds[len(mdds)//2]
        med_score = scores[len(scores)//2]
        print(f"  {strat_name:<16} {len(wr):>7} {n_passed:>6} "
              f"{n_passed/len(wr):>6.0%} {med_ret:>+8.1f} {med_mdd:>8.1f} "
              f"{med_score:>9.1f}")

    # Per-window V11 vs V10 delta
    print(f"\n  {'Window':>6} {'Period':<25} {'V10 Ret%':>8} {'V11 Ret%':>8} "
          f"{'Delta':>6} {'V10 MDD':>7} {'V11 MDD':>7}")
    print("  " + "-" * 75)
    v11_wins = 0
    for i in range(len(windows)):
        v10 = wfo_results["v10_baseline"][i]
        v11 = wfo_results["v11_winner"][i]
        delta = v11["return_pct"] - v10["return_pct"]
        if delta > 0:
            v11_wins += 1
        period = f"{v10['test_start']}→{v10['test_end']}"
        print(f"  {i:>6} {period:<25} {v10['return_pct']:>+8.1f} "
              f"{v11['return_pct']:>+8.1f} {delta:>+6.1f} "
              f"{v10['mdd_pct']:>7.1f} {v11['mdd_pct']:>7.1f}")
    print(f"\n  V11 wins: {v11_wins}/{len(windows)} windows ({v11_wins/len(windows):.0%})")

    with open(outdir / "wfo_fixed_results.json", "w") as f:
        json.dump(wfo_results, f, indent=2, default=str)

    # ====================================================================
    # PART 2: Enhanced Paired Bootstrap (5000 resamples, 3 block sizes)
    # ====================================================================
    print("\n" + "=" * 70)
    print("  PART 2: ENHANCED PAIRED BOOTSTRAP (5000 resamples × 3 block sizes)")
    print("=" * 70)

    # Full backtest for equity curves
    print("\n  Running full backtests for equity curves...")
    full_equity = {}
    for strat_name, factory in strategies.items():
        strat = factory()
        feed = DataFeed(DATA_PATH, start=START, end=END, warmup_days=WARMUP)
        cost = SCENARIOS["base"]
        engine = BacktestEngine(feed=feed, strategy=strat, cost=cost,
                                initial_cash=10_000.0, warmup_mode="no_trade")
        result = engine.run()
        full_equity[strat_name] = result.equity
        print(f"    {strat_name}: NAV={result.summary['final_nav_mid']:.0f}, "
              f"Sharpe={result.summary.get('sharpe', 'N/A')}")

    bootstrap_all = {}
    comparisons = [
        ("v11_winner", "v10_baseline", "V11 winner vs V10"),
        ("v11_wfo_opt", "v10_baseline", "V11 WFO-opt vs V10"),
        ("v11_winner", "v11_wfo_opt", "V11 winner vs WFO-opt"),
    ]
    for a_name, b_name, label in comparisons:
        print(f"\n  {label}:")
        bs_results = paired_bootstrap_enhanced(
            full_equity[a_name], full_equity[b_name],
            n_bootstrap=5000, block_sizes=[10, 20, 40], seed=42,
        )
        bootstrap_all[f"{a_name}_vs_{b_name}"] = bs_results
        for br in bs_results:
            print(f"    block={br['block_size']:>2}: delta={br['delta_observed']:+.4f} "
                  f"CI=[{br['ci_lower']:+.4f}, {br['ci_upper']:+.4f}] "
                  f"P(A>B)={br['p_a_better']:.1%}")

    # Also run across all 3 cost scenarios for V11 winner vs V10
    print(f"\n  V11 winner vs V10 — all scenarios (block=20, n=5000):")
    scenario_bootstrap = {}
    for scenario_name in SCENARIOS:
        strat_v11 = make_v11_winner()
        strat_v10 = V8ApexStrategy(V8ApexConfig())
        feed = DataFeed(DATA_PATH, start=START, end=END, warmup_days=WARMUP)
        cost = SCENARIOS[scenario_name]

        engine_v11 = BacktestEngine(feed=feed, strategy=strat_v11, cost=cost,
                                     initial_cash=10_000.0, warmup_mode="no_trade")
        res_v11 = engine_v11.run()

        strat_v10_2 = V8ApexStrategy(V8ApexConfig())
        feed2 = DataFeed(DATA_PATH, start=START, end=END, warmup_days=WARMUP)
        engine_v10 = BacktestEngine(feed=feed2, strategy=strat_v10_2, cost=cost,
                                     initial_cash=10_000.0, warmup_mode="no_trade")
        res_v10 = engine_v10.run()

        bs = paired_bootstrap_enhanced(
            res_v11.equity, res_v10.equity,
            n_bootstrap=5000, block_sizes=[20], seed=42,
        )[0]
        scenario_bootstrap[scenario_name] = bs
        print(f"    {scenario_name:<6}: delta={bs['delta_observed']:+.4f} "
              f"CI=[{bs['ci_lower']:+.4f}, {bs['ci_upper']:+.4f}] "
              f"P(V11>V10)={bs['p_a_better']:.1%}")

    bootstrap_all["scenarios"] = scenario_bootstrap

    with open(outdir / "bootstrap_enhanced.json", "w") as f:
        json.dump(bootstrap_all, f, indent=2)

    # ====================================================================
    # PART 3: Summary
    # ====================================================================
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)

    # WFO pass rates
    for sn in strategies:
        wr = wfo_results[sn]
        n_p = sum(1 for w in wr if w["return_pct"] > -5.0 and w["mdd_pct"] < 35.0)
        print(f"  WFO pass rate {sn}: {n_p}/{len(wr)} ({n_p/len(wr):.0%})")

    # Bootstrap consensus
    base_bs = bootstrap_all["v11_winner_vs_v10_baseline"]
    p_values = [br["p_a_better"] for br in base_bs]
    print(f"\n  P(V11 winner > V10) across block sizes: "
          f"{', '.join(f'{p:.1%}' for p in p_values)}")
    print(f"  Mean P(V11 > V10): {sum(p_values)/len(p_values):.1%}")

    wfo_opt_bs = bootstrap_all["v11_wfo_opt_vs_v10_baseline"]
    p_wfo = [br["p_a_better"] for br in wfo_opt_bs]
    print(f"  P(V11 WFO-opt > V10): {', '.join(f'{p:.1%}' for p in p_wfo)}")

    winner_vs_opt = bootstrap_all["v11_winner_vs_v11_wfo_opt"]
    p_wvo = [br["p_a_better"] for br in winner_vs_opt]
    print(f"  P(V11 winner > WFO-opt): {', '.join(f'{p:.1%}' for p in p_wvo)}")

    print(f"\n  Results saved to: {outdir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
