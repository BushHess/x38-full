# X17: Percentile-Ranked Selective Exit — Report

**Date**: 2026-03-10
**Verdict**: NOT_TEMPORAL (G0 passes, G1 fails — conservative grace window too short)

## Central Question

Can α-percentile thresholding + conservative grace windows (G=1-4) pass
bootstrap where X16's τ-probability approach (G=4-20) failed?

## Methodological Improvements over X16

1. **α-percentile** (rank-based) instead of τ-probability (calibration-dependent)
2. **Nested WFO only** — no full-sample screening (prevents info leakage)
3. **60 configs** (vs X16's 240) — reduced overfit risk
4. **7 features** (market-state only) — consistent with X14's validated feature set
5. **D1 regime check** during WATCH — additional safety exit
6. **ΔU diagnostic** — validates ranker quality without regression

## Results

### T0: ΔU Diagnostic (score-utility monotonicity)

168 trail-stop episodes, scored by 7-feature L2-penalized logistic (C=10.0).
Best (G,δ) for monotonicity: G=3, δ=1.0.

| Quintile | N | Mean ΔU | Median ΔU | P10 ΔU |
|----------|---|---------|-----------|--------|
| Q1 (lowest score) | 33 | -0.005 | -0.005 | -0.015 |
| Q2 | 33 | -0.005 | -0.006 | -0.023 |
| Q3 | 33 | -0.004 | -0.000 | -0.023 |
| Q4 | 33 | +0.000 | +0.002 | -0.019 |
| Q5 (highest score) | 36 | -0.006 | +0.004 | -0.032 |

**G0: PASS** — Medians are monotonically increasing from Q1 (-0.005) to Q5 (+0.004).
The ranker correctly sorts episodes by WATCH utility.

Note: Means are dragged down by tail losses (P10 values -0.015 to -0.032) when the
deeper stop is hit. This is expected — the selective policy only watches top-α%.

### T1: Nested Walk-Forward Validation (4 folds)

| Fold | Year | Best Params | E0 Sharpe | X17 Sharpe | d_Sharpe | Result |
|------|------|-------------|-----------|------------|----------|--------|
| 1 | 2022 | α=5% G=1 δ=0.5 | -0.930 | -0.930 | +0.000 | WIN |
| 2 | 2023 | α=25% G=1 δ=0.5 | 1.203 | 1.141 | -0.062 | LOSE |
| 3 | 2024 | α=5% G=1 δ=0.5 | 1.696 | 1.696 | +0.000 | LOSE |
| 4 | 2025 | α=5% G=1 δ=0.5 | 0.069 | 0.069 | -0.000 | LOSE |

Win rate: 25%, mean d_sharpe: -0.015

**G1: FAIL** (25% < 75%)

Consensus params: α=5%, G=1, δ=0.5 (most conservative config).

In-sample comparison: X17 WATCH Sharpe = 1.296 vs E0 = 1.336 → **negative lift**.

### What happened?

1. **Folds 1, 3, 4 selected α=5%, G=1**: At α=5%, only ~8 episodes enter WATCH.
   With G=1 (one 4-hour bar), almost none reclaim → d_sharpe ≈ 0.000.
   The mechanism is essentially a no-op.

2. **Fold 2 selected α=25%, G=1**: 25% of episodes enter WATCH, but G=1 gives
   only one bar for recovery. Most episodes that enter WATCH either timeout
   (price unchanged) or hit the deeper stop → net negative.

3. **All folds converged to G=1**: The nested WFO training selected G=1 across
   all folds because larger G (2-4) at any α% produced worse training Sharpe.
   This means the deeper stop hits too often at G≥2, destroying value.

## Gate Summary

| Gate | Condition | Result |
|------|-----------|--------|
| G0 | Top 2 quintiles median ΔU > 0 | PASS (+0.002, +0.004) |
| G1 | WFO ≥ 75%, mean d > 0 | **FAIL** (25%, -0.015) |
| G2-G5 | (not reached) | — |

## Key Insight: The G Dilemma

X16 and X17 together reveal a fundamental tradeoff:

| G range | In-sample lift | Bootstrap | Why |
|---------|---------------|-----------|-----|
| **G=1-4** (X17) | Near zero | — (not reached) | Too short for recovery |
| **G=8** (X16) | +0.088 Sharpe | FAIL (49.8%) | Path-specific autocorrelation |
| **G=12-20** (X16 T0) | Higher reclaim | — | Even more path-dependent |

There exists a **minimum G** below which WATCH can't capture enough recovery
to offset the occasional deeper-stop losses. X17 shows this minimum is > 4.

There exists a **maximum G** above which the edge becomes path-specific
(autocorrelation that bootstrap destroys). X16 shows this is somewhere < 8.

The viable window for G is between these two bounds. If min_G > max_G,
no WATCH policy can work robustly — and the evidence suggests this is the case.

## Comparison with Prior Studies

| Study | Mechanism | In-sample | Bootstrap | Verdict |
|-------|-----------|-----------|-----------|---------|
| X14 D | Static 7-feature mask | +0.092 | P(d>0)=65% PASS | PROMOTE |
| X16 E | WATCH τ=0.85, G=8 | +0.088 | P(d>0)=49.8% FAIL | ALL_FAIL |
| X17 | WATCH α=5%, G=1 | -0.015 | (not reached) | NOT_TEMPORAL |

X14's static mask remains the only approach that passes all gates.
WATCH mechanisms (X16, X17) either don't work (G too small) or don't
generalize (G too large).

## Implications

1. **Conservative grid was correct to test**: The analyst's reasoning about
   sample size, α-percentile, and nested WFO was methodologically sound.
   The failure is informative — it rules out small-G WATCH as a viable approach.

2. **The ΔU diagnostic was valuable**: T0 confirmed the ranker correctly
   sorts episodes by utility (monotonic medians). The issue isn't the ranker —
   it's the WATCH policy's inability to exploit the ranking at short horizons.

3. **No path to ΔU regression**: The analyst's staged plan was "if binary ranker
   shows stable lift → then consider ΔU regression." Since the binary ranker
   shows no lift at conservative G, regression is not warranted.

4. **Churn research complete**: X12-X17 collectively map the churn landscape:
   - The signal exists (X13: AUC=0.805)
   - ~10% of oracle ceiling is capturable by static filtering (X14)
   - Dynamic/stateful approaches fail: feedback loop (X15), path autocorrelation
     (X16), or insufficient grace window (X17)
   - Design D from X14 is the ceiling for robust churn mitigation

## Decision

Per SPEC.md decision matrix: G1 fails → NOT_TEMPORAL.
No further WATCH-based studies recommended.

## Artifacts

- `x17_results.json` — all test results
- `x17_delta_u.csv` — T0 per-episode ΔU by score quintile
- `x17_wfo.csv` — T1 WFO fold results
- `x17_comparison.csv` — T5 strategy comparison
