# X14: Trail-Stop Churn Filter — Design & Validation — Report

**Date**: 2026-03-09 (original), **Re-run**: 2026-03-17
**Verdict**: SCREEN_PASS_D (Design D passes all 6 research gates — confirmed 2026-03-17)
**Authority**: Research (standalone benchmark, NOT production pipeline)

## Central Question

X13 proved churn is predictable (AUC=0.805). Can a practical filter capture
this signal and survive out-of-sample validation?

## Method: Fixed-Sequence FWER Testing

Four designs tested A→B→C→D in order of increasing complexity.
First design to pass ALL 6 gates wins. Testing stops at first winner
(controls family-wise error rate).

### Gate Definitions

| Gate | Condition | Meaning |
|------|-----------|---------|
| G0 | In-sample d_sharpe > 0 | Filter improves over E0 baseline |
| G1 | WFO win_rate >= 3/4 | Temporally robust (4 expanding folds) |
| G2 | Bootstrap P(d_sharpe>0) > 60% | Robust across resampled paths |
| G3 | Bootstrap median d_mdd <= +5.0pp | MDD not materially worse |
| G4 | Jackknife: <= 2/6 negative folds | No single year drives the result |
| G5 | PSR > 0.95 (DOF-corrected) | Statistically significant Sharpe |

## Results

### T0: In-Sample Screening

| Design | Params | Sharpe | d_Sharpe | CAGR | MDD | Trades | Suppressed | G0 |
|--------|--------|--------|----------|------|-----|--------|------------|-----|
| E0 (baseline) | — | 1.336 | — | 55.3% | 42.0% | 186 | — | — |
| A (entry gate) | 0 | 1.267 | -0.069 | 51.5% | 42.0% | 183 | 35 | FAIL |
| B (ema_ratio) | 1 (tau) | 1.477 | +0.141 | 67.0% | 33.7% | 148 | 629 | PASS |
| C (ema+d1) | 2 (tau_ema, tau_d1) | 1.462 | +0.126 | 65.5% | 39.0% | 154 | 437 | PASS |
| D (logistic) | WFO model | 1.428 | +0.092 | 64.0% | 36.7% | 133 | 812 | PASS |

Design A fails immediately (suppresses wrong exits). B, C, D pass screening.

### T1: WFO Validation (4 expanding folds)

**Design B** (tau=1.035):
- Folds: WIN (+0.347), WIN (+0.312), LOSE (-0.003), WIN (+0.161)
- Win rate: 75%, mean d_sharpe: +0.204
- **G1: PASS**

**Design C** (tau_ema=1.04, tau_d1=0.02):
- Folds: WIN (+0.231), WIN (+0.127), LOSE (-0.141), LOSE (-0.059)
- Win rate: 50%, mean d_sharpe: +0.039
- **G1: FAIL** → C eliminated

**Design D** (logistic, per-fold retraining):
- Folds: WIN (+0.539), WIN (+0.199), LOSE (-0.034), WIN (+0.075)
- Win rate: 75%, mean d_sharpe: +0.195
- **G1: PASS**

### T2: Bootstrap (500 VCBB, Design B & D)

**Design B**:
- P(d_sharpe > 0): 57.6% — **G2: FAIL** → B eliminated
- Median d_mdd: +3.6pp

**Design D**:
- d_sharpe: median +0.058, [p5=-0.225, p95=+0.391]
- P(d_sharpe > 0): 65.0% — **G2: PASS**
- Median d_mdd: +2.4pp — **G3: PASS**

### T3: Jackknife (Design D, drop-one-year)

| Drop Year | E0 Sharpe | Filter Sharpe | d_Sharpe | Negative? |
|-----------|-----------|---------------|----------|-----------|
| 2020 | 0.821 | 0.839 | +0.018 | No |
| 2021 | 1.107 | 1.238 | +0.131 | No |
| 2022 | 1.446 | 1.542 | +0.096 | No |
| 2023 | 1.404 | 1.433 | +0.029 | No |
| 2024 | 1.268 | 1.403 | +0.135 | No |
| 2025 | 1.464 | 1.560 | +0.096 | No |

- 0/6 negative folds — **G4: PASS**
- Mean d_sharpe: +0.084, SE: 0.020
- Remarkably stable: all folds positive, no single year drives the result

### T4: PSR (Design D)

- E0 PSR: 1.000, Filter PSR: 1.000
- Effective DOF: 14.35 (Nyholt), extra DOF for model: 10
- n_eff (adjusted): 4,743
- **G5: PASS**

### T5: Comparison Table

| Strategy | Sharpe | CAGR | MDD | Trades |
|----------|--------|------|-----|--------|
| E0 (baseline) | 1.336 | 55.3% | 42.0% | 186 |
| E0+FilterD | 1.428 | 64.0% | 36.7% | 133 |
| E5 | 1.432 | 60.0% | 41.6% | 199 |
| Oracle | 2.181 | 121.6% | 29.3% | 82 |

Design D captures 10.9% of the oracle ceiling (+0.092 / +0.845 Sharpe).

## Sequential Testing Flow

```
A → FAIL G0 (d_sharpe = -0.069)
B → PASS G0 → PASS G1 → FAIL G2 (bootstrap 57.6% < 60%)
C → PASS G0 → FAIL G1 (WFO 50% < 75%)
D → PASS G0 → PASS G1 → PASS G2 → PASS G3 → PASS G4 → PASS G5 → WINNER
```

## Model Details (Design D)

- Type: L2-regularized logistic regression (Newton-Raphson, no sklearn)
- C: 10.0 (selected via 5-fold CV on training trail stops)
- Features: 7 effective (ema_ratio, atr_pctl, bar_range_atr, close_position,
  vdo_at_exit, d1_regime_str, trail_tightness) — 3 trade-context features
  (bars_held, dd_from_peak, bars_since_peak) are structurally zeroed in
  the static mask approach
- Training: on trail-stop exits, churn labelled as "recovery within 20 bars"
- WFO: retrained per fold (expanding window)
- Prediction: P(churn) > 0.5 → suppress trail stop

## Conclusions

1. **Simple filters (A/B/C) insufficient** — univariate/bivariate thresholds
   fail OOS validation (bootstrap or WFO)
2. **Design D (logistic model) passes all 6 gates** — only the multivariate
   model captures enough of the signal to survive validation
3. **Captures 10.9% of oracle ceiling** — modest but statistically validated
4. **Stable across all years** — jackknife 0/6 negative, no temporal dependency
5. **Bootstrap marginal** — 65% just above 60% threshold (95% CI includes 50%)

## Verdict: SCREEN_PASS_D

Design D passes all 6 research gates. To deploy, must be ported to `strategies/`,
registered in `STRATEGY_REGISTRY`, rebased onto E5_ema21D1 (not E0), and run
through the full production pipeline.

**Important**: X15 subsequently confirmed that the static 7-feature mask
is the CORRECT implementation. The 3 zeroed trade-context features act as
implicit regularization. Do NOT use dynamic 10-feature evaluation.

## Re-run 2026-03-17 (post-framework-fixes)

Updated numbers from latest re-run. Verdict unchanged: **SCREEN_PASS_D**.

| Metric | Original (2026-03-09) | Re-run (2026-03-17) | Change |
|--------|----------------------|---------------------|--------|
| Design D Sharpe | 1.428 | 1.530 | +0.102 |
| Design D CAGR | 64.0% | 70.7% | +6.7pp |
| Design D MDD | 36.7% | 35.9% | -0.8pp |
| Design D Trades | 133 | 148 | +15 |
| Bootstrap P(d>0) | 65.0% | 66.2% | +1.2pp |
| Jackknife neg | 0/6 | 0/6 | unchanged |
| WFO win rate | 3/4 (75%) | 3/4 (75%) | unchanged |

E0 baseline also shifted: Sharpe 1.336→1.372. All relative comparisons consistent.

## Artifacts

- `x14_results.json` — all test results
- `x14_screening.csv` — T0 in-sample results
- `x14_wfo_results.csv` — T1 WFO fold details
- `x14_bootstrap.csv` — T2 bootstrap distributions
- `x14_jackknife.csv` — T3 drop-one-year results
- `x14_comparison.csv` — T5 strategy comparison
