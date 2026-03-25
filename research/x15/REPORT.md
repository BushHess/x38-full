# X15: Churn Filter Integration — Dynamic Filter & Feature Fix — Report

**Date**: 2026-03-09
**Verdict**: ABORT (1/6 gates pass — dynamic filter catastrophically over-suppresses)

## Central Question

X14's Design D uses a static mask that zeros 3 trade-context features
(bars_held, dd_from_peak, bars_since_peak) because the mask is pre-computed
before the sim runs. These are top features in X13 (Cliff's d = 0.520, 0.458).
Does fixing this with dynamic evaluation at trail-stop time improve the filter?

## Results

### T0: Feature Fix Validation

| Variant | Sharpe | d_Sharpe | Trades | Suppressed | MDD |
|---------|--------|----------|--------|------------|-----|
| E0 (baseline) | 1.336 | — | 186 | — | 42.0% |
| X14 static (7 features) | 1.428 | +0.092 | 133 | 812 | 36.7% |
| **X15 dynamic (10 features)** | **1.030** | **-0.306** | **7** | **15,020** | **77.0%** |

**G0: FAIL** (X15 1.030 < X14 1.428)

The dynamic filter suppresses 15,020 out of ~15,027 trail stops, leaving
only 7 trades across 8+ years. Average hold time: 2,417 bars (~403 days).
The strategy holds through massive drawdowns because it never exits.

### T1: Feature Ablation

| Subset | Features | Sharpe | Trades | Suppressed |
|--------|----------|--------|--------|------------|
| All 10 | full set | 1.030 | 7 | 15,020 |
| 7 features | X14 equivalent | 1.386 | 133 | 821 |
| Top 4 | ema_ratio, bars_held, d1_regime, bar_range | 1.030 | 7 | 15,038 |
| ema_only | ema_ratio | 1.319 | 118 | 1,345 |

**Critical finding**: The 7-feature subset works fine (Sharpe 1.39, 133 trades).
Adding ANY of the 3 trade-context features causes immediate collapse to 7 trades.
The top_4 subset includes bars_held → same collapse.

**Root cause**: bars_held is positively correlated with churn. When the model
sees a trade has been held for many bars AND dd_from_peak is small, it
correctly predicts "this trail stop will be followed by recovery." But this is
true for ~99.95% of trail stops → suppress everything → hold forever.

### T2: WFO Validation (4 folds, dynamic filter)

| Fold | E0 Sharpe | Filter Sharpe | d_Sharpe | Result |
|------|-----------|---------------|----------|--------|
| 1 (2022) | -0.930 | -1.391 | -0.461 | LOSE |
| 2 (2023) | 1.203 | 2.445 | +1.242 | WIN |
| 3 (2024) | 1.696 | 1.768 | +0.072 | WIN |
| 4 (2025) | 0.069 | -0.280 | -0.350 | LOSE |

Win rate: 50%, mean d_sharpe: +0.126
**G1: FAIL** (need >= 75%)

### T3: Bootstrap (500 VCBB paths)

| Metric | Value |
|--------|-------|
| d_sharpe median | +0.207 |
| d_sharpe [p5, p95] | [-0.246, +0.772] |
| P(d_sharpe > 0) | 77.4% |
| d_mdd median | +10.83pp |
| d_mdd [p5, p95] | [-10.5pp, +32.3pp] |

**G2: PASS** (77.4% > 60%)
**G3: FAIL** (median d_mdd +10.83pp > +5.0pp)

Bootstrap shows the filter trades Sharpe for MDD — it avoids some bad exits
but holds through drawdowns that E0 would have exited.

### T4: Regime Monitor Interaction

| Variant | Sharpe | d_Sharpe | Trades |
|---------|--------|----------|--------|
| E0 | 1.336 | — | 186 |
| E0 + Filter | 1.030 | -0.306 | 7 |
| E0 + Monitor | 0.534 | -0.802 | 62 |
| E0 + Filter + Monitor | 0.323 | -1.013 | 4 |

Expected additive d_sharpe: -1.109
Actual combined d_sharpe: -1.013
Interaction penalty: +0.096

**G4: FAIL** (|0.096| > 0.05)

Both the filter and monitor independently degrade performance. Combined,
they leave only 4 trades — the strategy is essentially dead.

### T5: Retraining Sensitivity

| Train End | Test | d_sharpe (CV) | d_sharpe (fixed C) | C |
|-----------|------|---------------|--------------------|----|
| 2021-12 | 2022 | -0.461 | -0.461 | 10.0 |
| 2022-12 | 2023 | +1.242 | +1.242 | 10.0 |
| 2023-12 | 2024 | +0.072 | +0.072 | 10.0 |
| 2024-12 | 2025 | -0.350 | -0.313 | 10.0 |

Coefficient stability (std / |mean|):

| Feature | Drift |
|---------|-------|
| ema_ratio | 0.033 |
| bars_held | 0.098 |
| atr_pctl | 0.158 |
| bar_range_atr | 0.147 |
| dd_from_peak | 0.165 |
| bars_since_peak | 0.104 |
| close_position | 0.349 |
| **vdo_at_exit** | **0.543** |
| d1_regime_str | 0.150 |
| **trail_tightness** | **0.666** |

Max drift: 0.666 (trail_tightness)
**G5: FAIL** (0.666 > 0.50)

vdo_at_exit and trail_tightness are unstable across training windows.
C always selects 10.0 — the CV landscape is flat.

### T6: Comparison

| Strategy | Sharpe | CAGR | MDD | Trades | Avg Hold |
|----------|--------|------|-----|--------|----------|
| E0 | 1.336 | 55.3% | 42.0% | 186 | 41.3 |
| E0+FilterD(X15) | 1.030 | 55.1% | 77.0% | 7 | 2416.7 |
| E5 | 1.432 | 60.0% | 41.6% | 199 | 37.6 |
| Oracle | 2.181 | 121.6% | 29.3% | 82 | 99.3 |

## Gate Summary

| Gate | Condition | Result |
|------|-----------|--------|
| G0 | X15 d_sharpe > X14 d_sharpe | **FAIL** (1.030 < 1.428) |
| G1 | WFO >= 75% | **FAIL** (50%) |
| G2 | Bootstrap P(d_sharpe>0) > 60% | PASS (77.4%) |
| G3 | Median d_mdd <= +5.0pp | **FAIL** (+10.83pp) |
| G4 | Monitor interaction < 0.05 | **FAIL** (0.096) |
| G5 | Max coeff drift < 50% | **FAIL** (66.6%) |

**1/6 gates pass.**

## Key Insight

X14's "feature mismatch bug" was **implicit regularization**. The 3 zeroed
trade-context features (bars_held, dd_from_peak, bars_since_peak) prevented
the model from learning the unhelpful pattern: "almost all trail stops are
followed by recovery." This pattern is TRUE (churn rate 63%) but USELESS
as a filter — it leads to suppressing everything.

The 7-feature static mask works BECAUSE it lacks trade-context information.
The model can only use market-state features (ema_ratio, ATR, regime) to
make its prediction, which forces it to be more selective.

## Decision Matrix Outcome: ABORT

Per SPEC.md decision matrix:
> G0 fails (fix worse than broken) → ABORT — feature-available signal is weak

The dynamic filter destroys the filter's value. Design D's production
implementation MUST use X14's static pre-computed mask.

## Implications for Design D Integration

1. Use X14's static mask approach (pre-compute before sim)
2. Do NOT attempt to pass trade context (bars_held, dd_from_peak, bars_since_peak)
3. The 7 effective features are all market-state features available without trade context
4. Model retraining should use the same static feature extraction as X14

## Artifacts

- `x15_results.json` — all test results
- `x15_feature_fix.csv` — T0 X14 vs X15 comparison
- `x15_ablation.csv` — T1 feature subset results
- `x15_wfo_results.csv` — T2 WFO fold details
- `x15_bootstrap.csv` — T3 bootstrap distributions
- `x15_monitor_interaction.csv` — T4 factorial design
- `x15_retrain_sensitivity.csv` — T5 training window results
- `x15_comparison.csv` — T6 strategy comparison
