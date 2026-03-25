"""V11 comprehensive validation: full backtest + paired bootstrap + regime analysis.

Runs:
1. Full backtest: V10 baseline, V11 winner, buy-and-hold (all 3 cost scenarios)
2. Paired block bootstrap: V11 vs V10 (Sharpe difference)
3. Regime return decomposition for both
4. DD episode comparison
"""

import json
import math
import sys
from pathlib import Path

import numpy as np

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS, EquitySnap
from v10.research.bootstrap import (
    block_bootstrap,
    calc_sharpe,
    calc_cagr,
    calc_max_drawdown,
    run_bootstrap_suite,
    BootstrapResult,
    PERIODS_PER_YEAR_4H,
)
from v10.research.drawdown import detect_drawdown_episodes, recovery_table
from v10.research.objective import compute_objective
from v10.research.regime import classify_d1_regimes, compute_regime_returns
from v10.strategies.buy_and_hold import BuyAndHold
from v10.strategies.v8_apex import V8ApexConfig, V8ApexStrategy
from v10.strategies.v11_hybrid import V11HybridConfig, V11HybridStrategy


def make_v11_winner() -> V11HybridStrategy:
    """Create V11 with the winning cycle_late_only config."""
    cfg = V11HybridConfig()
    cfg.enable_cycle_phase = True
    cfg.cycle_early_aggression = 1.0
    cfg.cycle_early_trail_mult = 3.5
    cfg.cycle_late_aggression = 0.90
    cfg.cycle_late_trail_mult = 3.0
    cfg.cycle_late_max_exposure = 0.90
    return V11HybridStrategy(cfg)


def paired_bootstrap_sharpe(
    equity_a: list[EquitySnap],
    equity_b: list[EquitySnap],
    n_bootstrap: int = 2000,
    block_size: int = 20,
    seed: int = 42,
) -> dict:
    """Paired block bootstrap for Sharpe difference (A - B).

    Returns dict with delta stats and P(A > B).
    """
    navs_a = np.array([e.nav_mid for e in equity_a], dtype=np.float64)
    navs_b = np.array([e.nav_mid for e in equity_b], dtype=np.float64)

    # Align lengths
    n = min(len(navs_a), len(navs_b))
    ret_a = np.diff(navs_a[:n]) / navs_a[:n-1]
    ret_b = np.diff(navs_b[:n]) / navs_b[:n-1]

    observed_a = calc_sharpe(ret_a)
    observed_b = calc_sharpe(ret_b)
    observed_delta = observed_a - observed_b

    rng = np.random.default_rng(seed)
    m = len(ret_a)
    n_blocks = int(np.ceil(m / block_size))
    deltas = np.empty(n_bootstrap, dtype=np.float64)

    for i in range(n_bootstrap):
        starts = rng.integers(0, m, size=n_blocks)
        indices = np.concatenate([np.arange(s, s + block_size) % m for s in starts])[:m]
        sa = calc_sharpe(ret_a[indices])
        sb = calc_sharpe(ret_b[indices])
        deltas[i] = sa - sb

    return {
        "sharpe_a": round(observed_a, 4),
        "sharpe_b": round(observed_b, 4),
        "delta_observed": round(observed_delta, 4),
        "delta_mean": round(float(deltas.mean()), 4),
        "delta_std": round(float(deltas.std(ddof=1)), 4),
        "ci_lower": round(float(np.percentile(deltas, 2.5)), 4),
        "ci_upper": round(float(np.percentile(deltas, 97.5)), 4),
        "p_a_better": round(float((deltas > 0).mean()), 4),
        "n_bootstrap": n_bootstrap,
        "block_size": block_size,
    }


def main():
    data_path = "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
    outdir = Path("out/v11_full_validation")
    outdir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("  V11 COMPREHENSIVE VALIDATION")
    print("=" * 70)

    # Load data
    print("\nLoading data...")
    feed = DataFeed(data_path, start="2019-01-01", end="2026-02-20", warmup_days=365)
    print(f"  {feed}")

    # Define strategies
    strategies = {
        "v10_baseline": V8ApexStrategy(V8ApexConfig()),
        "v11_winner": make_v11_winner(),
        "buy_and_hold": BuyAndHold(),
    }

    # ====================================================================
    # 1. Full backtest across all cost scenarios
    # ====================================================================
    print("\n" + "=" * 70)
    print("  PART 1: FULL BACKTEST (all strategies × all scenarios)")
    print("=" * 70)

    all_results = {}
    for strat_name, strategy in strategies.items():
        all_results[strat_name] = {}
        for scenario_name, cost in SCENARIOS.items():
            # Need fresh strategy instance each time
            if strat_name == "v10_baseline":
                strat = V8ApexStrategy(V8ApexConfig())
            elif strat_name == "v11_winner":
                strat = make_v11_winner()
            else:
                strat = BuyAndHold()

            engine = BacktestEngine(
                feed=feed, strategy=strat, cost=cost,
                initial_cash=10_000.0, warmup_mode="no_trade",
            )
            result = engine.run()
            score = compute_objective(result.summary)
            all_results[strat_name][scenario_name] = {
                "result": result,
                "score": score,
                "summary": result.summary,
            }

    # Print comparison table
    print(f"\n  {'Strategy':<20} {'Scenario':<8} {'CAGR%':>8} {'MDD%':>8} "
          f"{'Sharpe':>8} {'PF':>8} {'Score':>8} {'Trades':>7}")
    print("  " + "-" * 85)
    for strat_name in strategies:
        for scenario_name in SCENARIOS:
            s = all_results[strat_name][scenario_name]["summary"]
            sc = all_results[strat_name][scenario_name]["score"]
            sharpe = s.get("sharpe")
            pf = s.get("profit_factor", 0)
            sharpe_str = f"{sharpe:8.2f}" if sharpe else "     N/A"
            pf_str = f"{pf:8.2f}" if isinstance(pf, (int, float)) else f"{'inf':>8}"
            print(f"  {strat_name:<20} {scenario_name:<8} "
                  f"{s.get('cagr_pct', 0):8.2f} "
                  f"{s.get('max_drawdown_mid_pct', 0):8.2f} "
                  f"{sharpe_str} {pf_str} {sc:8.2f} "
                  f"{s.get('trades', 0):>7}")

    # Save full summaries
    summary_data = {}
    for strat_name in strategies:
        summary_data[strat_name] = {}
        for scenario_name in SCENARIOS:
            summary_data[strat_name][scenario_name] = {
                "score": all_results[strat_name][scenario_name]["score"],
                **all_results[strat_name][scenario_name]["summary"],
            }
    with open(outdir / "full_comparison.json", "w") as f:
        json.dump(summary_data, f, indent=2, default=str)

    # ====================================================================
    # 2. Paired Bootstrap: V11 vs V10 (Sharpe difference)
    # ====================================================================
    print("\n" + "=" * 70)
    print("  PART 2: PAIRED BOOTSTRAP — V11 vs V10 (Sharpe)")
    print("=" * 70)

    bootstrap_results = {}
    for scenario_name in SCENARIOS:
        eq_v11 = all_results["v11_winner"][scenario_name]["result"].equity
        eq_v10 = all_results["v10_baseline"][scenario_name]["result"].equity

        pb = paired_bootstrap_sharpe(eq_v11, eq_v10, n_bootstrap=2000, seed=42)
        bootstrap_results[scenario_name] = pb

        print(f"\n  [{scenario_name}] V11 Sharpe={pb['sharpe_a']}, "
              f"V10 Sharpe={pb['sharpe_b']}")
        print(f"    Delta: {pb['delta_observed']:+.4f} "
              f"(mean={pb['delta_mean']:+.4f}, std={pb['delta_std']:.4f})")
        print(f"    95% CI: [{pb['ci_lower']:+.4f}, {pb['ci_upper']:+.4f}]")
        print(f"    P(V11 > V10): {pb['p_a_better']:.1%}")

    with open(outdir / "paired_bootstrap.json", "w") as f:
        json.dump(bootstrap_results, f, indent=2)

    # ====================================================================
    # 3. Individual bootstrap for V11 winner (base scenario)
    # ====================================================================
    print("\n" + "=" * 70)
    print("  PART 3: INDIVIDUAL BOOTSTRAP — V11 winner (base scenario)")
    print("=" * 70)

    eq_v11_base = all_results["v11_winner"]["base"]["result"].equity
    v11_bootstrap = run_bootstrap_suite(eq_v11_base, n_bootstrap=2000, seed=42)
    for br in v11_bootstrap:
        print(f"  {br.metric_name:>20}: observed={br.observed:.4f}, "
              f"CI=[{br.ci_lower:.4f}, {br.ci_upper:.4f}], "
              f"P>0={br.p_positive:.1%}")

    v11_bs_data = [
        {
            "metric": br.metric_name,
            "observed": br.observed,
            "mean": br.mean,
            "std": br.std,
            "ci_lower": br.ci_lower,
            "ci_upper": br.ci_upper,
            "p_positive": br.p_positive,
        }
        for br in v11_bootstrap
    ]
    with open(outdir / "v11_bootstrap.json", "w") as f:
        json.dump(v11_bs_data, f, indent=2)

    # ====================================================================
    # 4. Regime return decomposition
    # ====================================================================
    print("\n" + "=" * 70)
    print("  PART 4: REGIME RETURN DECOMPOSITION")
    print("=" * 70)

    regimes = classify_d1_regimes(feed.d1_bars)
    regime_data = {}

    for strat_name in ["v10_baseline", "v11_winner"]:
        eq = all_results[strat_name]["base"]["result"].equity
        rr = compute_regime_returns(eq, feed.d1_bars, regimes)
        regime_data[strat_name] = rr

    print(f"\n  {'Regime':<12} {'V10 Return%':>12} {'V11 Return%':>12} {'Delta':>8} "
          f"{'V10 MDD%':>10} {'V11 MDD%':>10}")
    print("  " + "-" * 70)
    for regime_name in ["BULL", "TOPPING", "BEAR", "CHOP", "SHOCK", "NEUTRAL"]:
        v10_r = regime_data["v10_baseline"].get(regime_name, {})
        v11_r = regime_data["v11_winner"].get(regime_name, {})
        v10_ret = v10_r.get("total_return_pct", 0)
        v11_ret = v11_r.get("total_return_pct", 0)
        delta = v11_ret - v10_ret
        v10_mdd = v10_r.get("max_dd_pct", 0)
        v11_mdd = v11_r.get("max_dd_pct", 0)
        print(f"  {regime_name:<12} {v10_ret:>12.2f} {v11_ret:>12.2f} {delta:>+8.2f} "
              f"{v10_mdd:>10.2f} {v11_mdd:>10.2f}")

    with open(outdir / "regime_comparison.json", "w") as f:
        json.dump(regime_data, f, indent=2)

    # ====================================================================
    # 5. Drawdown episodes comparison
    # ====================================================================
    print("\n" + "=" * 70)
    print("  PART 5: DRAWDOWN EPISODES (base scenario, ≥5%)")
    print("=" * 70)

    dd_data = {}
    for strat_name in ["v10_baseline", "v11_winner"]:
        eq = all_results[strat_name]["base"]["result"].equity
        episodes = detect_drawdown_episodes(eq, min_dd_pct=5.0)
        table = recovery_table(episodes)
        dd_data[strat_name] = table
        print(f"\n  {strat_name}: {len(table)} episodes ≥5%")
        for ep in table[:5]:
            print(f"    {ep['peak_date']} → {ep['trough_date']}: "
                  f"-{ep['drawdown_pct']:.1f}%, "
                  f"recovery: {ep.get('days_to_recovery', 'N/A')} days")

    with open(outdir / "dd_episodes.json", "w") as f:
        json.dump(dd_data, f, indent=2, default=str)

    # ====================================================================
    # 6. Score summary
    # ====================================================================
    print("\n" + "=" * 70)
    print("  FINAL SCORE COMPARISON")
    print("=" * 70)

    for scenario_name in SCENARIOS:
        v10_sc = all_results["v10_baseline"][scenario_name]["score"]
        v11_sc = all_results["v11_winner"][scenario_name]["score"]
        bh_sc = all_results["buy_and_hold"][scenario_name]["score"]
        delta = v11_sc - v10_sc
        print(f"  {scenario_name:<8}: V10={v10_sc:7.2f}  V11={v11_sc:7.2f}  "
              f"delta={delta:+6.2f}  B&H={bh_sc:7.2f}")

    print("\n" + "=" * 70)
    print("  Results saved to:", outdir)
    print("=" * 70)


if __name__ == "__main__":
    main()
