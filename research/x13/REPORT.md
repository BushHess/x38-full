# X13: Is Trail-Stop Churn Predictable? — Report

**Date**: 2026-03-09
**Verdict**: INFORMATION_EXISTS (AUC=0.805, perm p=0.002)

## Central Question

At the moment a trail stop fires, does enough information exist to distinguish
true reversals (good exits) from churn (premature exits)?

## Results

### P0: Oracle Ceiling

| Metric | E0 Baseline | Oracle | Delta |
|--------|-------------|--------|-------|
| Sharpe | 1.336 | 2.181 | +0.845 |
| CAGR | 55.3% | 121.6% | +66.3pp |
| MDD | 42.0% | 29.3% | -12.7pp |
| Trades | 186 | 82 | -104 |

The oracle suppresses all churn trail stops (those followed by recovery within
20 bars). This establishes the theoretical ceiling: +0.845 Sharpe available
if we could perfectly predict churn.

**V0 PASS**: Oracle ceiling is large enough to pursue.

### P1: Feature Engineering

10 features computed at trail-stop trigger time:

| Feature | Cliff's d | Rank | Description |
|---------|-----------|------|-------------|
| ema_ratio | +0.567 | 1 | EMA_fast / EMA_slow at exit |
| bars_held | +0.520 | 2 | Duration of trade in bars |
| d1_regime_str | +0.458 | 3 | D1 EMA regime strength |
| bar_range_atr | -0.300 | 4 | Bar range / ATR |
| bars_since_peak | +0.203 | 5 | Bars since trade peak |
| vdo_at_exit | +0.172 | 6 | VDO value at exit |
| dd_from_peak | -0.160 | 7 | Drawdown from peak |
| atr_pctl | +0.151 | 8 | ATR percentile (100-bar window) |
| trail_tightness | -0.030 | 9 | Trail stop tightness |
| close_position | +0.020 | 10 | Close position in bar range |

Top 3 features all have medium-to-large effect sizes (d > 0.4).

**V1 PASS**: Multiple features have significant univariate separation.

### P2: Multivariate Model (L2-Logistic)

| Metric | Value |
|--------|-------|
| LOOCV AUC | 0.805 |
| Best C | 10.0 |
| Permutation p-value | 0.002 (500 shuffles) |
| Null AUC mean ± std | 0.466 ± 0.067 |
| Youden threshold | 0.58 |

Confusion matrix (at Youden threshold):
- TP=83, FP=19, FN=23, TN=43
- Sensitivity: 78%, Specificity: 69%

All 10 features have non-zero coefficients (no feature eliminated by L2).

**V2 PASS**: AUC=0.805 significantly above random (p=0.002).

### P3: Bootstrap Validation (500 VCBB paths)

| Metric | Value |
|--------|-------|
| AUC median | 0.681 |
| AUC [5%, 95%] | [0.562, 0.774] |
| P(AUC > 0.60) | 86.8% |
| P(AUC > 0.55) | 97.0% |
| Best permutation p median | 7.8e-7 |
| P(perm p < 0.05) | 100% |

The signal degrades from 0.805 (in-sample) to 0.681 (median OOS) —
expected shrinkage. But P(AUC > 0.60) = 86.8% confirms the signal
is real, not a fluke of the specific data path.

**V3 PASS**: Bootstrap confirms signal robustness.

### P4: Churn Window Sensitivity

Tested churn windows: 10, 15, 20, 30, 40 bars.
All 5 windows show significant AUC (stable_count = 5/5).

**V4 PASS**: Signal is not sensitive to churn definition window.

## Conclusions

1. **Oracle ceiling is +0.845 Sharpe** — substantial room for improvement
2. **Top features**: ema_ratio, bars_held, d1_regime_str (all d > 0.4)
3. **LOOCV AUC = 0.805** — strong predictive signal, not random (p=0.002)
4. **Bootstrap median AUC = 0.681** — signal survives OOS with expected shrinkage
5. **Signal is stable** across all churn window definitions (10-40 bars)
6. **All 4 verification gates pass** (V0-V4)

## Verdict: INFORMATION_EXISTS

Sufficient information exists at trail-stop time to predict churn with
AUC >> 0.5. The Pareto frontier (Sharpe vs trade count) is theoretically
breakable. Next step: design and validate a practical filter (→ X14).

## Artifacts

- `x13_results.json` — all phase results
- `x13_oracle.csv`, `x13_features.csv`, `x13_univariate.csv`
- `x13_multivariate.csv`, `x13_bootstrap.csv`, `x13_sensitivity.csv`
