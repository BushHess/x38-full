#!/usr/bin/env python3
"""WFO round-by-round robustness: per-window metrics for V10 vs V11.

For each of 10 OOS windows:
  - Run V10 baseline and V11 WFO-opt under harsh scenario
  - Compute: score, CAGR, MDD, Sharpe, trades, turnover, fees, regime returns
  - Compute delta (V11 - V10) for each metric
  - Sign test on delta_harsh_score

Output:
  - per_round_metrics.csv
  - sign_test.json
  - stdout (redirect to log)
"""

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

np.seterr(all="ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS, Bar
from v10.research.objective import compute_objective
from v10.research.regime import classify_d1_regimes, compute_regime_returns
from v10.research.wfo import generate_windows
from v10.strategies.v8_apex import V8ApexConfig, V8ApexStrategy
from v10.strategies.v11_hybrid import V11HybridConfig, V11HybridStrategy

DATA_PATH = "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
START = "2019-01-01"
END = "2026-02-20"
WARMUP_DAYS = 365
OUTDIR = Path("out_v11_validation_stepwise")


def make_v10():
    return V8ApexStrategy(V8ApexConfig())


def make_v11():
    cfg = V11HybridConfig()
    cfg.enable_cycle_phase = True
    cfg.cycle_early_aggression = 1.0
    cfg.cycle_early_trail_mult = 3.5
    cfg.cycle_late_aggression = 0.95
    cfg.cycle_late_trail_mult = 2.8
    cfg.cycle_late_max_exposure = 0.90
    return V11HybridStrategy(cfg)


def run_window(factory, test_start, test_end, scenario="harsh"):
    """Run backtest on a single OOS window. Returns summary + equity."""
    cost = SCENARIOS[scenario]
    strategy = factory()
    feed = DataFeed(DATA_PATH, start=test_start, end=test_end,
                    warmup_days=WARMUP_DAYS)
    engine = BacktestEngine(feed=feed, strategy=strategy, cost=cost,
                            initial_cash=10_000.0)
    result = engine.run()
    return result, feed


def extract_metrics(result, feed):
    """Extract full metric set from a backtest result."""
    s = result.summary
    score = compute_objective(s)

    # Regime returns
    regimes = classify_d1_regimes(feed.d1_bars)
    rr = compute_regime_returns(result.equity, feed.d1_bars, regimes)
    bull_ret = rr.get("BULL", {}).get("total_return_pct", 0.0)
    topping_ret = rr.get("TOPPING", {}).get("total_return_pct", 0.0)

    return {
        "harsh_score": score,
        "cagr_pct": s.get("cagr_pct", 0.0),
        "mdd_pct": s.get("max_drawdown_mid_pct", 0.0),
        "sharpe": s.get("sharpe") or 0.0,
        "trades": s.get("trades", 0),
        "turnover_per_year": s.get("turnover_per_year", 0.0),
        "fees_total": s.get("fees_total", 0),
        "final_nav": s.get("final_nav_mid", 10000.0),
        "total_return_pct": s.get("total_return_pct", 0.0),
        "bull_return_pct": bull_ret,
        "topping_return_pct": topping_ret,
    }


def sign_test_pvalue(deltas):
    """Exact binomial sign test: H0: P(delta>0) = 0.5.

    Returns one-sided p-value for P(delta>0) > 0.5.
    Zeros (ties) excluded.
    """
    non_zero = [d for d in deltas if abs(d) > 1e-12]
    n = len(non_zero)
    if n == 0:
        return 1.0
    k = sum(1 for d in non_zero if d > 0)
    # P(X >= k) where X ~ Binomial(n, 0.5)
    # = sum_{i=k}^{n} C(n,i) * 0.5^n
    p = 0.0
    for i in range(k, n + 1):
        p += math.comb(n, i) * (0.5 ** n)
    return p


def main():
    windows = generate_windows(START, END, train_months=24, test_months=6, slide_months=6)
    print("=" * 70)
    print("  WFO ROUND-BY-ROUND ROBUSTNESS (harsh scenario)")
    print("=" * 70)
    print(f"  Windows: {len(windows)}")
    print(f"  Baseline: V8ApexConfig() defaults")
    print(f"  Candidate: V11 WFO-optimal (0.95/2.8/0.90)")
    print(f"  Scenario: harsh (50 bps RT)")
    print()

    csv_rows = []
    deltas_score = []
    deltas_cagr = []
    deltas_mdd = []

    metric_keys = ["harsh_score", "cagr_pct", "mdd_pct", "sharpe", "trades",
                   "turnover_per_year", "fees_total", "final_nav",
                   "total_return_pct", "bull_return_pct", "topping_return_pct"]

    for w in windows:
        print(f"  Window {w.window_id}: OOS {w.test_start} → {w.test_end}")

        res_v10, feed_v10 = run_window(make_v10, w.test_start, w.test_end)
        res_v11, feed_v11 = run_window(make_v11, w.test_start, w.test_end)

        m_v10 = extract_metrics(res_v10, feed_v10)
        m_v11 = extract_metrics(res_v11, feed_v11)

        # Compute deltas
        m_delta = {}
        for k in metric_keys:
            v10_val = m_v10[k] if isinstance(m_v10[k], (int, float)) else 0
            v11_val = m_v11[k] if isinstance(m_v11[k], (int, float)) else 0
            m_delta[k] = v11_val - v10_val

        deltas_score.append(m_delta["harsh_score"])
        deltas_cagr.append(m_delta["cagr_pct"])
        deltas_mdd.append(m_delta["mdd_pct"])

        # CSV rows
        for label, m in [("V10", m_v10), ("V11_WFO_opt", m_v11), ("DELTA", m_delta)]:
            row = {"window_id": w.window_id, "oos_start": w.test_start,
                   "oos_end": w.test_end, "strategy": label}
            for k in metric_keys:
                val = m[k]
                if isinstance(val, float):
                    row[k] = f"{val:.4f}"
                else:
                    row[k] = str(val)
            csv_rows.append(row)

        # Print summary
        d_sc = m_delta["harsh_score"]
        sign = "+" if d_sc > 0 else ("-" if d_sc < 0 else "=")
        print(f"    V10: score={m_v10['harsh_score']:.2f}  ret={m_v10['total_return_pct']:+.1f}%  "
              f"mdd={m_v10['mdd_pct']:.1f}%  trades={m_v10['trades']}")
        print(f"    V11: score={m_v11['harsh_score']:.2f}  ret={m_v11['total_return_pct']:+.1f}%  "
              f"mdd={m_v11['mdd_pct']:.1f}%  trades={m_v11['trades']}")
        print(f"    Delta score: {d_sc:+.2f} [{sign}]  "
              f"BULL: {m_delta['bull_return_pct']:+.1f}%  "
              f"TOPPING: {m_delta['topping_return_pct']:+.1f}%")
        print()

    # ── Write CSV ──────────────────────────────────────────────────────
    csv_path = OUTDIR / "per_round_metrics.csv"
    fieldnames = ["window_id", "oos_start", "oos_end", "strategy"] + metric_keys
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"  Saved: {csv_path}")

    # ── Statistics ─────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  AGGREGATE STATISTICS")
    print("=" * 70)

    n_positive = sum(1 for d in deltas_score if d > 1e-12)
    n_negative = sum(1 for d in deltas_score if d < -1e-12)
    n_zero = sum(1 for d in deltas_score if abs(d) <= 1e-12)
    n_total = len(deltas_score)

    sorted_deltas = sorted(deltas_score)
    median_delta = sorted_deltas[len(sorted_deltas) // 2]
    worst_delta = min(deltas_score)
    best_delta = max(deltas_score)
    mean_delta = sum(deltas_score) / len(deltas_score)

    p_sign = sign_test_pvalue(deltas_score)

    print(f"  count(delta_harsh > 0): {n_positive}/{n_total}")
    print(f"  count(delta_harsh = 0): {n_zero}/{n_total}")
    print(f"  count(delta_harsh < 0): {n_negative}/{n_total}")
    print(f"  median(delta_harsh):    {median_delta:+.4f}")
    print(f"  mean(delta_harsh):      {mean_delta:+.4f}")
    print(f"  worst_round_delta:      {worst_delta:+.4f} (window {deltas_score.index(worst_delta)})")
    print(f"  best_round_delta:       {best_delta:+.4f} (window {deltas_score.index(best_delta)})")
    print(f"  sign test p-value:      {p_sign:.4f} (one-sided, H0: P(delta>0)=0.5)")

    # ── Robustness conclusion ──────────────────────────────────────────
    # Threshold: "robust" if >= 60% of non-zero rounds have delta>0
    #            AND worst_round_delta > -5.0 (score points)
    WORST_THRESHOLD = -5.0

    non_zero_count = n_positive + n_negative
    positive_rate = n_positive / non_zero_count if non_zero_count > 0 else 0

    robust = positive_rate >= 0.60 and worst_delta > WORST_THRESHOLD
    concentration = n_zero / n_total  # how many rounds show NO difference

    print(f"\n  Non-zero rounds: {non_zero_count}/{n_total}")
    print(f"  Positive rate (among non-zero): {positive_rate:.0%} ({n_positive}/{non_zero_count})")
    print(f"  Concentration (zero-delta rounds): {concentration:.0%}")
    print(f"  Worst round > {WORST_THRESHOLD}? {'YES' if worst_delta > WORST_THRESHOLD else 'NO'}")

    if n_zero / n_total > 0.5:
        conclusion = (
            f"INCONCLUSIVE — {n_zero}/{n_total} rounds show zero delta "
            f"(V11 cycle only fires in bull periods). "
            f"Among {non_zero_count} active rounds: {n_positive} positive, {n_negative} negative. "
            f"Improvement NOT concentrated in 1 round but limited to few rounds."
        )
    elif robust:
        conclusion = (
            f"ROBUST — {n_positive}/{non_zero_count} non-zero rounds positive "
            f"(>= 60% threshold), worst delta = {worst_delta:+.2f} > {WORST_THRESHOLD} threshold."
        )
    else:
        conclusion = (
            f"NOT ROBUST — only {n_positive}/{non_zero_count} non-zero rounds positive "
            f"or worst delta = {worst_delta:+.2f} exceeds {WORST_THRESHOLD} threshold."
        )

    print(f"\n  CONCLUSION: {conclusion}")

    # ── Save sign test ─────────────────────────────────────────────────
    sign_test_data = {
        "n_windows": n_total,
        "n_positive": n_positive,
        "n_negative": n_negative,
        "n_zero": n_zero,
        "median_delta_harsh": round(median_delta, 4),
        "mean_delta_harsh": round(mean_delta, 4),
        "worst_round_delta": round(worst_delta, 4),
        "worst_round_window": deltas_score.index(worst_delta),
        "best_round_delta": round(best_delta, 4),
        "best_round_window": deltas_score.index(best_delta),
        "sign_test_pvalue": round(p_sign, 6),
        "sign_test_note": (
            "One-sided exact binomial test, H0: P(delta>0) = 0.5. "
            "Ties (delta=0) excluded. "
            f"With {n_zero} ties out of {n_total}, effective n = {non_zero_count}."
        ),
        "all_deltas_score": [round(d, 4) for d in deltas_score],
        "all_deltas_cagr": [round(d, 4) for d in deltas_cagr],
        "all_deltas_mdd": [round(d, 4) for d in deltas_mdd],
        "conclusion": conclusion,
        "robustness_criteria": {
            "positive_rate_threshold": ">=60% of non-zero rounds",
            "worst_round_threshold": f"> {WORST_THRESHOLD} score points",
        },
    }

    sign_path = OUTDIR / "sign_test.json"
    with open(sign_path, "w") as f:
        json.dump(sign_test_data, f, indent=2)
    print(f"\n  Saved: {sign_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
