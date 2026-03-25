#!/usr/bin/env python3
"""WFO round-by-round robustness — RETURN-BASED metrics (no score rejection).

Motivation: B1 (score-based) showed 8/10 windows with delta=0 because
compute_objective() returns -1M when trades < 10. This masks real differences.

This script uses 4 return-based primary metrics:
  1. total_return_pct — raw return, no rejection
  2. score_no_reject  — same formula as objective but WITHOUT the <10 trades guard
  3. sharpe            — risk-adjusted, computed by engine (0 if undefined)
  4. mdd_pct           — drawdown comparison (lower = better)

Statistical tests:
  - Sign test (exact binomial) on each metric's delta
  - Wilcoxon signed-rank test on non-zero deltas (scipy if available, else manual)
  - Magnitude analysis: sum of positive vs negative deltas

Output:
  - per_round_return_metrics.csv
  - sign_test_returns.json
  - stdout
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
from v10.core.types import SCENARIOS
from v10.research.regime import classify_d1_regimes, compute_regime_returns
from v10.research.wfo import generate_windows
from v10.strategies.v8_apex import V8ApexConfig, V8ApexStrategy
from v10.strategies.v11_hybrid import V11HybridConfig, V11HybridStrategy

DATA_PATH = "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
START = "2019-01-01"
END = "2026-02-20"
WARMUP_DAYS = 365
OUTDIR = Path("out_v11_validation_stepwise")


# ── Score formula WITHOUT rejection ──────────────────────────────────────

def compute_score_no_reject(summary: dict) -> float:
    """Same formula as compute_objective but WITHOUT the <10 trades rejection.

    When n_trades < 10, still computes the score from available metrics.
    This allows comparing strategies on short OOS windows where trade count
    is naturally low.
    """
    cagr = summary.get("cagr_pct", 0.0)
    max_dd = summary.get("max_drawdown_mid_pct", 0.0)
    sharpe = summary.get("sharpe") or 0.0
    pf = summary.get("profit_factor", 0.0) or 0.0
    if isinstance(pf, str):  # "inf"
        pf = 3.0
    n_trades = summary.get("trades", 0)

    score = (
        2.5 * cagr
        - 0.60 * max_dd
        + 8.0 * max(0.0, sharpe)
        + 5.0 * max(0.0, min(pf, 3.0) - 1.0)
        + min(n_trades / 50.0, 1.0) * 5.0
    )
    return score


# ── Strategy factories ───────────────────────────────────────────────────

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


# ── Backtest runner ──────────────────────────────────────────────────────

def run_window(factory, test_start, test_end, scenario="harsh"):
    cost = SCENARIOS[scenario]
    strategy = factory()
    feed = DataFeed(DATA_PATH, start=test_start, end=test_end,
                    warmup_days=WARMUP_DAYS)
    engine = BacktestEngine(feed=feed, strategy=strategy, cost=cost,
                            initial_cash=10_000.0)
    result = engine.run()
    return result, feed


# ── Metrics extraction (return-based) ────────────────────────────────────

def extract_metrics(result, feed):
    s = result.summary
    score_nr = compute_score_no_reject(s)

    regimes = classify_d1_regimes(feed.d1_bars)
    rr = compute_regime_returns(result.equity, feed.d1_bars, regimes)
    bull_ret = rr.get("BULL", {}).get("total_return_pct", 0.0)
    topping_ret = rr.get("TOPPING", {}).get("total_return_pct", 0.0)

    return {
        "score_no_reject": score_nr,
        "total_return_pct": s.get("total_return_pct", 0.0),
        "cagr_pct": s.get("cagr_pct", 0.0),
        "sharpe": s.get("sharpe") or 0.0,
        "mdd_pct": s.get("max_drawdown_mid_pct", 0.0),
        "profit_factor": s.get("profit_factor", 0.0) or 0.0,
        "trades": s.get("trades", 0),
        "final_nav": s.get("final_nav_mid", 10000.0),
        "fees_total": s.get("fees_total", 0),
        "bull_return_pct": bull_ret,
        "topping_return_pct": topping_ret,
    }


# ── Statistical tests ────────────────────────────────────────────────────

def sign_test_pvalue(deltas):
    """Exact binomial sign test: H0: P(delta>0) = 0.5.
    Returns one-sided p-value. Ties excluded.
    """
    non_zero = [d for d in deltas if abs(d) > 1e-12]
    n = len(non_zero)
    if n == 0:
        return 1.0
    k = sum(1 for d in non_zero if d > 0)
    p = 0.0
    for i in range(k, n + 1):
        p += math.comb(n, i) * (0.5 ** n)
    return p


def wilcoxon_signed_rank(deltas):
    """Manual Wilcoxon signed-rank test (no scipy dependency).

    Returns (W+, W-, n_eff, p_approx).
    For small n, uses normal approximation (conservative).
    """
    non_zero = [(abs(d), 1 if d > 0 else -1) for d in deltas if abs(d) > 1e-12]
    n = len(non_zero)
    if n < 2:
        return 0, 0, n, 1.0

    # Rank by absolute value
    non_zero.sort(key=lambda x: x[0])
    ranks = list(range(1, n + 1))

    # Handle ties: average ranks
    i = 0
    while i < n:
        j = i + 1
        while j < n and abs(non_zero[j][0] - non_zero[i][0]) < 1e-12:
            j += 1
        if j > i + 1:
            avg_rank = sum(ranks[i:j]) / (j - i)
            for k_idx in range(i, j):
                ranks[k_idx] = avg_rank
        i = j

    w_plus = sum(ranks[i] for i in range(n) if non_zero[i][1] > 0)
    w_minus = sum(ranks[i] for i in range(n) if non_zero[i][1] < 0)

    # Normal approximation for p-value
    mu = n * (n + 1) / 4.0
    sigma = math.sqrt(n * (n + 1) * (2 * n + 1) / 24.0)
    if sigma < 1e-12:
        return w_plus, w_minus, n, 1.0

    # One-sided: P(W+ >= observed) under H0
    z = (w_plus - mu) / sigma
    # Approximate P(Z >= z) using error function
    p = 0.5 * (1.0 - math.erf(z / math.sqrt(2.0)))

    return w_plus, w_minus, n, p


def sign_test_stats(deltas, label):
    """Compute full stats for a metric's deltas."""
    n_total = len(deltas)
    n_pos = sum(1 for d in deltas if d > 1e-12)
    n_neg = sum(1 for d in deltas if d < -1e-12)
    n_zero = sum(1 for d in deltas if abs(d) <= 1e-12)
    n_eff = n_pos + n_neg

    mean_d = sum(deltas) / n_total if n_total > 0 else 0
    sorted_d = sorted(deltas)
    median_d = sorted_d[n_total // 2] if n_total > 0 else 0

    # Sum of positive / negative magnitudes
    sum_pos = sum(d for d in deltas if d > 1e-12)
    sum_neg = sum(d for d in deltas if d < -1e-12)

    p_sign = sign_test_pvalue(deltas)
    w_plus, w_minus, w_n, p_wilcoxon = wilcoxon_signed_rank(deltas)

    return {
        "metric": label,
        "n_total": n_total,
        "n_positive": n_pos,
        "n_negative": n_neg,
        "n_zero": n_zero,
        "n_effective": n_eff,
        "mean_delta": round(mean_d, 6),
        "median_delta": round(median_d, 6),
        "sum_positive": round(sum_pos, 4),
        "sum_negative": round(sum_neg, 4),
        "net_magnitude": round(sum_pos + sum_neg, 4),
        "sign_test_pvalue": round(p_sign, 6),
        "wilcoxon_W_plus": round(w_plus, 2),
        "wilcoxon_W_minus": round(w_minus, 2),
        "wilcoxon_n_eff": w_n,
        "wilcoxon_pvalue": round(p_wilcoxon, 6),
        "all_deltas": [round(d, 4) for d in deltas],
    }


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    windows = generate_windows(START, END, train_months=24, test_months=6,
                               slide_months=6)
    print("=" * 70)
    print("  WFO ROUND-BY-ROUND — RETURN-BASED METRICS (no score rejection)")
    print("=" * 70)
    print(f"  Windows: {len(windows)}")
    print(f"  Baseline: V10 = V8ApexConfig() defaults")
    print(f"  Candidate: V11 WFO-opt (0.95/2.8/0.90)")
    print(f"  Scenario: harsh (50 bps RT)")
    print(f"  Primary metrics: total_return_pct, score_no_reject, sharpe, mdd_pct")
    print()

    metric_keys = ["score_no_reject", "total_return_pct", "cagr_pct", "sharpe",
                   "mdd_pct", "profit_factor", "trades", "final_nav", "fees_total",
                   "bull_return_pct", "topping_return_pct"]

    csv_rows = []
    deltas = {k: [] for k in metric_keys}

    for w in windows:
        print(f"  Window {w.window_id}: OOS {w.test_start} → {w.test_end}")

        res_v10, feed_v10 = run_window(make_v10, w.test_start, w.test_end)
        res_v11, feed_v11 = run_window(make_v11, w.test_start, w.test_end)

        m_v10 = extract_metrics(res_v10, feed_v10)
        m_v11 = extract_metrics(res_v11, feed_v11)

        m_delta = {}
        for k in metric_keys:
            v10_val = m_v10[k] if isinstance(m_v10[k], (int, float)) else 0
            v11_val = m_v11[k] if isinstance(m_v11[k], (int, float)) else 0
            m_delta[k] = v11_val - v10_val
            deltas[k].append(m_delta[k])

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

        # Per-window print
        d_ret = m_delta["total_return_pct"]
        d_snr = m_delta["score_no_reject"]
        print(f"    V10: score_nr={m_v10['score_no_reject']:+.2f}  "
              f"ret={m_v10['total_return_pct']:+.2f}%  "
              f"sharpe={m_v10['sharpe']:.3f}  "
              f"mdd={m_v10['mdd_pct']:.2f}%  "
              f"trades={m_v10['trades']}")
        print(f"    V11: score_nr={m_v11['score_no_reject']:+.2f}  "
              f"ret={m_v11['total_return_pct']:+.2f}%  "
              f"sharpe={m_v11['sharpe']:.3f}  "
              f"mdd={m_v11['mdd_pct']:.2f}%  "
              f"trades={m_v11['trades']}")
        sign_r = "+" if d_ret > 0.001 else ("-" if d_ret < -0.001 else "=")
        sign_s = "+" if d_snr > 0.001 else ("-" if d_snr < -0.001 else "=")
        print(f"    Δ ret: {d_ret:+.2f}% [{sign_r}]  "
              f"Δ score_nr: {d_snr:+.2f} [{sign_s}]  "
              f"Δ BULL: {m_delta['bull_return_pct']:+.2f}%  "
              f"Δ TOPPING: {m_delta['topping_return_pct']:+.2f}%")
        print()

    # ── Write CSV ─────────────────────────────────────────────────────────
    csv_path = OUTDIR / "per_round_return_metrics.csv"
    fieldnames = ["window_id", "oos_start", "oos_end", "strategy"] + metric_keys
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"  Saved: {csv_path}")

    # ── Multi-metric sign tests ──────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  RETURN-BASED SIGN TESTS")
    print("=" * 70)

    primary_metrics = ["total_return_pct", "score_no_reject", "sharpe", "mdd_pct"]
    all_stats = {}

    for metric in primary_metrics:
        st = sign_test_stats(deltas[metric], metric)
        all_stats[metric] = st

        print(f"\n  ── {metric} ──")
        print(f"  Positive / Zero / Negative: {st['n_positive']} / {st['n_zero']} / {st['n_negative']} (of {st['n_total']})")
        print(f"  Mean delta:    {st['mean_delta']:+.6f}")
        print(f"  Median delta:  {st['median_delta']:+.6f}")
        print(f"  Sum positive:  {st['sum_positive']:+.4f}")
        print(f"  Sum negative:  {st['sum_negative']:+.4f}")
        print(f"  Net magnitude: {st['net_magnitude']:+.4f}")
        print(f"  Sign test p:   {st['sign_test_pvalue']:.4f}  (n_eff={st['n_effective']})")
        if st['wilcoxon_n_eff'] >= 2:
            print(f"  Wilcoxon W+:   {st['wilcoxon_W_plus']:.1f}  W-: {st['wilcoxon_W_minus']:.1f}  "
                  f"p: {st['wilcoxon_pvalue']:.4f}  (n_eff={st['wilcoxon_n_eff']})")

    # ── Robustness summary ───────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  ROBUSTNESS SUMMARY")
    print("=" * 70)

    # For return_pct: "robust" if >= 60% of non-zero rounds positive
    # AND worst delta > -5.0 return points
    # For mdd_pct: delta < 0 means V11 has LESS drawdown (better)
    RETURN_WORST_THRESHOLD = -5.0  # percentage points
    POSITIVE_RATE_THRESHOLD = 0.60

    results = {}
    for metric in primary_metrics:
        st = all_stats[metric]
        n_eff = st["n_effective"]

        if metric == "mdd_pct":
            # For MDD, negative delta = V11 has lower MDD = BETTER
            pos_rate = st["n_negative"] / n_eff if n_eff > 0 else 0
            worst = max(deltas[metric])  # worst = most positive = V11 has higher MDD
            label_good = "n_negative (V11 lower MDD)"
            n_good = st["n_negative"]
        else:
            pos_rate = st["n_positive"] / n_eff if n_eff > 0 else 0
            worst = min(deltas[metric])
            label_good = "n_positive"
            n_good = st["n_positive"]

        if n_eff == 0:
            verdict = "NO DATA"
        elif st["n_zero"] / st["n_total"] > 0.5:
            verdict = "INCONCLUSIVE (>50% ties)"
        elif pos_rate >= POSITIVE_RATE_THRESHOLD and worst > RETURN_WORST_THRESHOLD:
            verdict = "PASS"
        else:
            verdict = "FAIL"

        results[metric] = {
            "positive_rate": round(pos_rate, 4),
            "n_good": n_good,
            "n_eff": n_eff,
            "worst_delta": round(worst, 4),
            "verdict": verdict,
        }

        print(f"\n  {metric}:")
        print(f"    {label_good}: {n_good}/{n_eff} = {pos_rate:.0%}")
        print(f"    Worst delta: {worst:+.4f}")
        print(f"    Verdict: {verdict}")

    # ── Overall conclusion ───────────────────────────────────────────────
    verdicts = [r["verdict"] for r in results.values()]
    n_pass = verdicts.count("PASS")
    n_fail = verdicts.count("FAIL")
    n_inc = verdicts.count("INCONCLUSIVE (>50% ties)")
    n_nodata = verdicts.count("NO DATA")

    if n_pass >= 3:
        overall = "ROBUST"
    elif n_fail >= 2:
        overall = "NOT ROBUST"
    elif n_inc >= 2:
        overall = "INCONCLUSIVE"
    else:
        overall = "MIXED"

    conclusion_parts = []
    for metric in primary_metrics:
        r = results[metric]
        conclusion_parts.append(f"{metric}: {r['verdict']} ({r['n_good']}/{r['n_eff']})")

    conclusion = (
        f"{overall} — " + "; ".join(conclusion_parts)
    )

    print(f"\n  {'=' * 50}")
    print(f"  OVERALL: {conclusion}")
    print(f"  {'=' * 50}")

    # ── Save JSON ────────────────────────────────────────────────────────
    sign_data = {
        "description": "Return-based round-by-round robustness (no score rejection)",
        "scenario": "harsh (50 bps RT)",
        "baseline": "V10 = V8ApexConfig()",
        "candidate": "V11 WFO-opt (0.95/2.8/0.90)",
        "n_windows": len(windows),
        "primary_metrics": primary_metrics,
        "metric_stats": all_stats,
        "robustness_results": results,
        "overall_conclusion": conclusion,
        "robustness_criteria": {
            "positive_rate_threshold": f">={POSITIVE_RATE_THRESHOLD:.0%} of non-zero rounds",
            "worst_delta_threshold": f"> {RETURN_WORST_THRESHOLD}",
            "overall_pass": ">=3 of 4 primary metrics PASS",
        },
        "supplementary_deltas": {
            "bull_return_pct": [round(d, 4) for d in deltas["bull_return_pct"]],
            "topping_return_pct": [round(d, 4) for d in deltas["topping_return_pct"]],
            "cagr_pct": [round(d, 4) for d in deltas["cagr_pct"]],
            "fees_total": [round(d, 4) for d in deltas["fees_total"]],
        },
    }

    json_path = OUTDIR / "sign_test_returns.json"
    with open(json_path, "w") as f:
        json.dump(sign_data, f, indent=2)
    print(f"\n  Saved: {json_path}")
    print(f"  Saved: {csv_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
