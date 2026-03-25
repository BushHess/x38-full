# V11 cycle_late_only Validation Report

**Strategy:** V11 Hybrid (cycle_late_only)
**Baseline:** V10 = V8ApexConfig()
**WFO-optimal params:** aggression=0.95, trail_mult=2.8, max_exposure=0.90
**Evaluation period:** 2019-01-01 to 2026-02-20 (7.14 years)
**Report date:** 2026-02-23

---

## Executive Summary

| Step | Test | Verdict |
|------|------|---------|
| A | Reproducibility | **PASS** |
| B1 | WFO Round-by-Round (score) | INCONCLUSIVE (negative) |
| B1b | WFO Round-by-Round (return) | INCONCLUSIVE (positive, weak) |
| B2 | Sensitivity Grid | **FAIL** (22% beat, cliff risk) |
| B3 | Final Holdout | **HOLD** (V11 loses on 3/3 scenarios) |
| C | Selection Bias (PBO/DSR) | **PASS** |
| D | Lookahead Sanity | **PASS** |
| E | TOPPING vs LATE_BULL Alignment | **PASS** (0% overlap) |
| F | Risk Overlays | **HOLD** (OV3 harsh-only) |

**Decision: HOLD** — Do not promote V11 cycle_late_only over V10 at this time.

---

## A. Reproducibility

V10 and V11 backtests were verified deterministic — identical SHA256 hashes across repeated runs with identical inputs. No floating-point drift or state leakage detected.

**Verdict: PASS**

---

## B1. WFO Round-by-Round (Score-Based)

10 rolling OOS windows (24m train / 6m test / 6m slide), harsh scenario.

**Results:**
- 8/10 windows: zero delta (V11 cycle phase never fires — bear/chop/neutral periods)
- 2 active windows: both negative (window 6: -1.57, window 7: -4.32)
- 0 positive rounds out of 2 effective
- Sign test p-value: 1.0 (no evidence of improvement)

The cycle_late_only feature only activates during extended bull runs, which occurred in only 2 of 10 OOS windows. In both, V11 underperformed V10.

**Data:** [per_round_metrics.csv](../per_round_metrics.csv)
**Verdict: INCONCLUSIVE** — insufficient effective samples, but directionally negative

---

## B1b. WFO Round-by-Round (Return-Based)

Same windows, using `score_no_reject` (no <10 trade rejection) and `total_return_pct`.

| Metric | +Δ | -Δ | =0 | Mean Δ | Wilcoxon p |
|--------|----|----|----|----|------------|
| total_return_pct | 2 | 2 | 6 | +0.41% | 0.233 |
| score_no_reject | 2 | 2 | 6 | +3.00 | 0.233 |
| sharpe | 3 | 1 | 6 | +0.028 | 0.137 |
| mdd_pct | 0 | 1 | 9 | -0.087 | 1.000 |

When V11 fires, the magnitudes are asymmetric — positive deltas (+16.5, +19.3 score_no_reject) outweigh negatives (-1.6, -4.3). Net magnitude: +30.0.

**Verdict: INCONCLUSIVE** — positive in magnitude but not statistically significant

---

## B2. Sensitivity Grid

27-point grid: aggression ∈ {0.85, 0.90, 0.95} × trail_mult ∈ {2.7, 3.0, 3.3} × max_exposure ∈ {0.75, 0.90, 0.95}

| Scenario | Beat V10 | % Beat | Best Δ | Worst Δ | Mean Δ |
|----------|----------|--------|--------|---------|--------|
| harsh | 6/27 | 22.2% | +2.10 | -7.59 | -2.24 |
| base | 6/27 | 22.2% | +2.20 | -8.65 | -2.60 |
| smart | 6/27 | 22.2% | +2.22 | -8.58 | -2.55 |

Winners cluster tightly: only (aggression=0.95, trail_mult≥3.0) beats V10. Average neighbor beat rate: 47.9% — cliff risk confirmed. The best improvement (+2.1 harsh) sits at the grid edge.

**Data:** [sensitivity_grid.csv](../sensitivity_grid.csv)
**Verdict: FAIL** — 22% < 60% threshold, cliff risk present

---

## B3. Final Holdout

Last 17 months (2024-10-01 to 2026-02-20), one-shot evaluation.

| Scenario | V10 Score | V11 Score | Δ Score | V11 CAGR | V10 CAGR |
|----------|-----------|-----------|---------|----------|----------|
| harsh | 34.66 | 33.43 | **-1.23** | 16.85% | 17.29% |
| base | 55.06 | 53.78 | **-1.28** | 23.89% | 24.35% |
| smart | 64.64 | 63.31 | **-1.32** | 27.17% | 27.65% |

V11 loses on all 3 scenarios. The delta is small (1-2%) but consistent. Regime decomposition shows the loss comes entirely from BULL return (-0.73 to -0.83 pp) — V11's tighter trail in LATE_BULL clips some recovery upside. TOPPING, BEAR, SHOCK, CHOP, NEUTRAL returns are identical.

**Data:** [final_holdout_metrics.csv](../final_holdout_metrics.csv)
**Verdict: HOLD** — V11 marginally behind, within noise margin but directionally negative

---

## C. Selection Bias (PBO + DSR)

Combinatorial Symmetric Cross-Validation across 28 configs × 10 blocks.

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| PBO | 0.139 | < 0.50 | **PASS** |
| Mean OOS rank | 5.93 / 28 | — | Top 21% |
| Median OOS rank | 2.5 / 28 | — | Top 9% |
| DSR p-value | 1.0 | ≥ 0.95 | **PASS** |
| Observed Sharpe | 1.147 | — | — |
| E[max SR | null] | 0.107 | — | — |

The strategy is not data-mined. PBO of 13.9% indicates low probability of backtest overfitting. DSR confirms the observed Sharpe ratio is statistically significant.

**Data:** [selection_bias_results.json](../selection_bias_results.json)
**Verdict: PASS**

---

## D. Lookahead Sanity

16 structural tests checking for future data leakage in indicators, signals, and execution.

All 16 tests passed. No lookahead bias detected.

**Verdict: PASS**

---

## E. TOPPING vs LATE_BULL Alignment

Does V11's LATE_BULL cycle phase overlap with TOPPING regime (the regime with largest drawdown)?

| Metric | Value |
|--------|-------|
| Evaluation days | 2,608 |
| TOPPING days | 102 (3.91%) |
| LATE_BULL days | 106 (4.06%) |
| Overlap | **0 days (0%)** |
| Jaccard similarity | 0.0% |

TOPPING uses EMA50 proximity (< 1% distance) + low ADX. LATE_BULL uses EMA200 distance (≥ 40%) + high RSI. These are structurally orthogonal by design — a price cannot simultaneously be within 1% of EMA50 and 40%+ above EMA200.

**Implication:** Any LATE_BULL-specific modification (OV1) has zero impact on TOPPING drawdown. TOPPING solutions must target TOPPING-specific signals (momentum deceleration, HMA break).

**Data:** [overlap_topping_latebull.csv](../overlap_topping_latebull.csv), [topping_vs_latebull.json](../topping_vs_latebull.json)
**Verdict: PASS** (aligned — no conflation)

---

## F. Risk Overlays for TOPPING Drawdown

Three exit-only overlays tested on V11 cycle_late_only base:

### Overlay 1: Late-Bull Pyramid Ban + Trail Tightening

Block adds in LATE_BULL + tighter trail (1.8/2.0/2.2 vs base 2.8).

| Variant | Harsh Score | Δ vs V11 | BULL Return | TOPPING Return |
|---------|------------|----------|-------------|----------------|
| trail_1.8 | 72.77 | -18.03 | 785.83% | -21.04% |
| trail_2.0 | 80.99 | -9.81 | 948.97% | -21.04% |
| trail_2.2 | 82.77 | -8.03 | 972.85% | -21.04% |

**REJECT** — Zero TOPPING impact (confirmed by E: no overlap). Massive BULL sacrifice.

### Overlay 2: Position Peak-to-Trough Stop

Exit on position DD > X% or > Y×ATR from peak.

| Variant | Harsh Score | Δ vs V11 | TOPPING Return | MDD |
|---------|------------|----------|----------------|-----|
| pct_5 | 83.68 | -7.12 | -12.31% | 36.29% |
| atr_3 | 79.09 | -11.71 | -9.13% | 38.70% |
| atr_2 | 45.40 | -45.40 | -8.57% | 31.03% |

**REJECT** — Reduces TOPPING damage but extra exits create severe turnover penalty (up to 222 trades vs 103 baseline).

### Overlay 3: Deceleration Tightening

Tighten trail when momentum acceleration < 0 for N consecutive bars (± HMA break, ± sizing reduction).

Initial grid (5 variants): best was ov3_b8_t2.5 (score=97.0, +8.1 vs V10) but WFO=40% < 60% threshold.

**Regularized grid** (72 variants): widened bars {5-10} × trail {2.0-3.0} × HMA {T/F} × sizing {0.5,1.0}.

| Promoted Variant | Harsh Score | Δ vs V10 | MDD | TOPPING | WFO Win% |
|------------------|------------|----------|-----|---------|----------|
| b5_t3.0_hN_s0.5 | 95.54 | +6.60 | 35.44% | -19.93% | **70%** |
| b5_t3.0_hY_s0.5 | 95.88 | +6.94 | 35.91% | -19.45% | **60%** |
| b7_t3.0_hN_s0.5 | 94.42 | +5.48 | 36.26% | -20.10% | **60%** |

However, cross-scenario analysis revealed these improvements are **harsh-only**:
- Base scenario: regresses ~4.7 pts vs V11
- Smart scenario: regresses ~8.4 pts vs V11

The overlays improve only when transaction costs are high enough (50 bps) to make the avoided drawdowns worthwhile. At lower costs, the extra exits are net negative.

**Data:** [overlay_results.csv](../overlay_results.csv), [overlay_wfo.csv](../overlay_wfo.csv), [ov3_refined_grid.csv](../ov3_refined_grid.csv)
**Verdict: HOLD** — OV3 promising under harsh costs but not robust across cost scenarios

---

## Paired Bootstrap (Supplementary)

Block bootstrap (5,000 resamples, block=20) of Sharpe ratio difference:

| Scenario | Δ Sharpe | 95% CI | P(V11 > V10) |
|----------|----------|--------|---------------|
| harsh | +0.019 | [-0.005, +0.053] | 91.7% |
| base | +0.019 | [-0.005, +0.053] | 92.2% |
| smart | +0.020 | [-0.005, +0.053] | 92.4% |

CI includes zero → not significant at 5% level. Consistent with WFO inconclusive finding.

**Data:** [paired_bootstrap.csv](../paired_bootstrap.csv)

---

## Full-Period Performance Summary

| Strategy | Scenario | Score | CAGR | MDD | Sharpe | Trades |
|----------|----------|-------|------|-----|--------|--------|
| V10 | harsh | 88.94 | 37.26% | 36.28% | 1.151 | 103 |
| V11 | harsh | 90.80 | 37.93% | 36.28% | 1.170 | 103 |
| **Δ** | **harsh** | **+1.86** | **+0.67%** | **0.0%** | **+0.019** | **0** |
| V10 | base | 112.74 | 45.55% | 34.78% | 1.322 | 100 |
| V11 | base | 114.65 | 46.24% | 34.78% | 1.341 | 100 |
| **Δ** | **base** | **+1.91** | **+0.69%** | **0.0%** | **+0.019** | **0** |
| V10 | smart | 121.37 | 48.56% | 34.07% | 1.386 | 100 |
| V11 | smart | 123.30 | 49.26% | 34.07% | 1.405 | 100 |
| **Δ** | **smart** | **+1.93** | **+0.70%** | **0.0%** | **+0.020** | **0** |

**Data:** [summary_full_backtest.csv](../summary_full_backtest.csv)

---

## Decision: HOLD

**V11 cycle_late_only is NOT promoted over V10.**

### Quantitative Justification

1. **Marginal improvement**: +1.86 score (2.1%) on full-period harsh — barely above noise floor
2. **Sensitivity fragility**: Only 6/27 (22%) of parameter grid beats V10. Winners cluster at one corner (high aggression + high trail_mult). Any small parameter perturbation loses.
3. **Holdout failure**: V11 loses -1.23 to -1.32 on the last 17 months across all cost scenarios. The feature adds no value in the most recent market regime.
4. **WFO inconsistency**: Of 10 OOS windows, V11 is active in only 2. In those 2, score-based metrics are negative. Return-based metrics are mixed (2+, 2-).
5. **Bootstrap**: 95% CI for Sharpe delta includes zero — improvement not statistically significant.
6. **Risk overlays**: No overlay variant achieves robust cross-scenario improvement. Best OV3 works only under harsh costs.

### What IS Validated

- **No overfitting**: PBO=13.9%, DSR passes. The strategy family is legitimate.
- **No lookahead**: 16/16 structural tests pass.
- **Clean design**: TOPPING and LATE_BULL are orthogonal — no signal conflation.
- **V10 remains strong**: 37.26% CAGR, 1.151 Sharpe, 36.28% MDD under harsh costs.

### Recommendation

Keep V10 (V8ApexConfig) as the production strategy. V11 cycle_late_only should be shelved as a research direction. The cycle phase detection infrastructure is sound but the current implementation's alpha is too small and too fragile to justify deployment risk.

If revisiting, focus on:
- Widening the activation window (LATE_BULL triggers on only 4% of days)
- Trail_mult sensitivity (cliff at 2.7→3.0 boundary)
- OV3 deceleration overlay as a standalone V10 enhancement (bypassing cycle phase entirely)

---

## Appendix: File Index

See [../index.txt](../index.txt) for complete listing of all output files.

## Appendix: Score Formula

```
score = 2.5 * cagr
      - 0.60 * max_dd
      + 8.0 * max(0, sharpe)
      + 5.0 * max(0, min(pf, 3) - 1)
      + min(n_trades / 50, 1) * 5
```

Returns -1,000,000 if trades < 10.

## Appendix: Cost Scenarios

| Scenario | Round-trip Cost |
|----------|----------------|
| smart | 13 bps |
| base | 31 bps |
| harsh | 50 bps |
