# X15: Churn Filter Integration — Design D Production Pipeline

## Context

X14 proved Design D (WFO logistic model) passes all 6 gates:
- Sharpe 1.428 (+0.092 vs E0), MDD 36.7% (-5.3pp), 133 trades
- WFO 3/4, bootstrap P(d_sharpe>0)=65%, jackknife 0/6 negative

Design D runs PARALLEL to E5+EMA1D21 — both PROMOTE. Future data validates.

## Critical Bug in X14: Feature Engineering Mismatch

X14's `_mask_design_d` builds a STATIC boolean mask before the sim runs.
At each bar i, it computes 10 features — but 3 depend on trade state:

| Feature | Depends on trade? | X14 value | Correct value |
|---------|-------------------|-----------|---------------|
| bars_held | YES | 0 (unknown) | i - entry_bar |
| dd_from_peak | YES | 0 (unknown) | (peak - close) / peak |
| bars_since_peak | YES | 0 (unknown) | i - peak_bar |

These 3 features ARE available at trail-stop time (the sim tracks entry_bar,
peak price, and peak bar). X14 zeroed them because the mask is pre-computed.

**X15 fixes this** by moving to a DYNAMIC filter: evaluate the logistic model
AT each trail-stop trigger with full trade context.

This is not just a bug fix — it may significantly change performance because
bars_held and dd_from_peak are top-3 features in X13 (Cliff's d = 0.520
and 0.458 medium/large). The model is currently predicting with 60% of its
information missing.

## Study Objectives

1. **Fix feature mismatch**: Dynamic filter with all 10 features at trail-stop time
2. **Compare**: Fixed 10-feature model vs X14's broken 7-feature model
3. **Retraining pipeline**: How to train the model in production
4. **Regime monitor interaction**: Does the filter conflict with the monitor?
5. **Sensitivity**: Retrain frequency, lookback window, C stability, feature drift
6. **Feature ablation**: Which features actually matter at inference time?

## Architecture: Dynamic vs Static Filter

### X14 (static mask — BROKEN for 3 features)
```
1. Precompute mask[n] for all bars
2. Run sim with mask → suppress if mask[i] = True
Problem: mask computed WITHOUT trade context → features 2, 5, 6 zeroed
```

### X15 (dynamic filter — CORRECT)
```
1. Train model on historical trail stops (full 10 features)
2. Store: weights w, standardization (mu, std), regularization C
3. In sim: at each bar where trail stop fires AND we're in a trade:
   a. Compute all 10 features using current trade state
   b. Predict P(churn) from model
   c. Suppress if P(churn) > 0.5
```

Modified sim interface:
```python
def _run_sim_dynamic(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                     trail_mult=TRAIL, cps=CPS_HARSH,
                     model_w=None, model_mu=None, model_std=None):
    """Sim with dynamic logistic filter evaluated at trail-stop time."""
    # At trail stop trigger:
    #   feat = compute_10_features(i, entry_bar, peak, peak_bar, ...)
    #   feat_s = (feat - model_mu) / model_std
    #   z = dot(append(feat_s, 1.0), model_w)
    #   if sigmoid(z) > 0.5: suppress
```

## Test Suite

### T0: Feature Fix Validation

Compare X14 (static, 7 working features) vs X15 (dynamic, all 10 features).

**Method:**
1. Train logistic model on full data (identical to X14 T0)
2. Run X14-style static sim → baseline (reproduces X14 results)
3. Run X15-style dynamic sim → fixed version
4. Compare: Sharpe, CAGR, MDD, trades, trail suppressions

**Expected:** X15 dynamic should be BETTER than X14 static because bars_held
and dd_from_peak are strong predictors (X13 top-3 features).

**Artefact:** `x15_feature_fix.csv`

### T1: Feature Ablation

Test which features contribute at inference time.

**Method:** Train 10-feature model, then test with subsets:
- A: All 10 features (baseline)
- B: 7 features only (drop bars_held, dd_from_peak, bars_since_peak — X14 equivalent)
- C: Top 4 only (ema_ratio, bars_held, d1_regime_str, bar_range_atr — X13 top)
- D: ema_ratio only (strongest single feature)

For each: run full-data sim, compare metrics.

**Artefact:** `x15_ablation.csv`

### T2: WFO Validation (4 folds, dynamic filter)

Same WFO structure as X14 but with dynamic filter.

**Method:** 4 expanding folds (train from wi, test yearly 2022-2026).
In each fold:
1. Run E0 on training data → get trail stops
2. Label churn (churn_window=20)
3. Extract 10 features (WITH trade context)
4. Select C via 5-fold CV on training trail stops
5. Fit logistic model on training data
6. Run dynamic-filter sim on full data, extract test window metrics

**Gate:** win_rate >= 3/4 AND mean_d_sharpe > 0

**Artefact:** `x15_wfo_results.csv`

### T3: Bootstrap Validation (500 VCBB)

Same as X14 T2 but with dynamic filter.

**Method:** 500 VCBB paths, seed=42, block=60.
For each path:
1. Split: train on first 60%, test on full path
2. Run E0 sim on full path → trail stops in training portion → label → fit model
3. Run dynamic-filter sim on full path with trained model
4. Record d_sharpe, d_cagr, d_mdd

**Gate:** P(d_sharpe > 0) > 0.60 AND median d_mdd <= +5.0 pp

**Artefact:** `x15_bootstrap.csv`

### T4: Regime Monitor Interaction

Test whether the churn filter conflicts with the regime monitor.

**Method:** Run 4 sim variants:
- E0 (baseline)
- E0 + Filter (churn filter only)
- E0 + Monitor (regime monitor only)
- E0 + Filter + Monitor (both)

Compare: is (Filter + Monitor) additive or does one cancel the other?

**Expected:** Filter operates at trail-stop exits, Monitor blocks entries.
Different mechanisms → should be additive. If not, identify conflicts.

**Gate:** Factorial d_sharpe(Filter+Monitor) >= d_sharpe(Filter) + d_sharpe(Monitor) - 0.05
(Allow 0.05 Sharpe interaction penalty — both can't be strictly additive
because they change trade populations.)

**Artefact:** `x15_monitor_interaction.csv`

### T5: Retraining Sensitivity

How often does the model need retraining?

**Method:** Train model at different points, test on subsequent data:
- Train on 2019-2021, test on 2022 (3yr lookback)
- Train on 2019-2022, test on 2023 (4yr lookback)
- Train on 2019-2023, test on 2024 (5yr lookback)
- Train on 2019-2024, test on 2025-2026 (6yr lookback)

For each: record test Sharpe, model coefficients, C value.

**Check coefficient stability:** Do the logistic weights drift significantly
across training windows? If weights are stable, infrequent retraining is OK.
If they drift, need periodic retraining.

**Also test:** Fixed-C (C=1.0) vs per-window-CV C. If similar performance,
use fixed C for simplicity.

**Artefact:** `x15_retrain_sensitivity.csv`

### T6: Comprehensive Comparison Table

Side-by-side: E0, E0+Filter(X15 fixed), E0+Filter(X14 broken), E5, Oracle.

**Artefact:** `x15_comparison.csv`

## Verdict Gates

| Gate | Condition | Meaning |
|------|-----------|---------|
| **G0** | T0 X15 d_sharpe > X14 d_sharpe | Feature fix improves over broken version |
| **G1** | T2 WFO win_rate >= 3/4 | Temporally robust |
| **G2** | T3 P(d_sharpe > 0) > 0.60 | Bootstrap robust |
| **G3** | T3 median d_mdd <= +5.0 pp | MDD not materially worse |
| **G4** | T4 interaction_penalty < 0.05 | Monitor compatibility |
| **G5** | T5 coeff stability (max drift < 50%) | Retrain infrequently OK |

ALL gates pass → **INTEGRATE**: Design D churn filter is production-ready.
Run parallel to E5+EMA1D21 for forward validation.

## Decision Matrix

| Outcome | Action |
|---------|--------|
| All gates pass | INTEGRATE — add to strategy as optional flag |
| G0 fails (fix worse than broken) | ABORT — feature-available signal is weak |
| G1 or G2 fails | HOLD — dynamic filter doesn't improve OOS |
| G4 fails | SEPARATE — filter and monitor conflict, run only one |
| G5 fails | RETRAIN_REQUIRED — need periodic model refresh |

## Implementation Notes

### Model Storage (for production)

```python
# After training:
model_state = {
    "weights": w.tolist(),          # (n_features + 1,)
    "mu": mu.tolist(),              # (n_features,)
    "std": std.tolist(),            # (n_features,)
    "C": best_c,                    # regularization
    "feature_names": FEATURE_NAMES, # ordered feature list
    "train_end_date": "2024-12-31", # last training data
    "churn_window": 20,             # bars for churn definition
    "n_train_samples": n_samples,   # trail stops used for training
}
# Save as JSON alongside strategy config
```

### Feature Computation at Trail-Stop Time

```python
def compute_features_at_trail_stop(i, entry_bar, peak_px, peak_bar,
                                   cl, hi, lo, at, ef, es, vd,
                                   d1_str_h4, trail_mult):
    """Compute all 10 features at bar i when trail stop fires."""
    f1 = ef[i] / es[i]                           # ema_ratio
    f2 = float(i - entry_bar)                     # bars_held ← NOW AVAILABLE
    f3 = atr_percentile(at, i, window=100)        # atr_pctl
    f4 = (hi[i] - lo[i]) / at[i]                  # bar_range_atr
    f5 = (peak_px - cl[i]) / peak_px              # dd_from_peak ← NOW AVAILABLE
    f6 = float(i - peak_bar)                      # bars_since_peak ← NOW AVAILABLE
    f7 = (cl[i] - lo[i]) / (hi[i] - lo[i])       # close_position
    f8 = vd[i]                                    # vdo_at_exit
    f9 = d1_str_h4[i]                             # d1_regime_str
    f10 = trail_mult * at[i] / cl[i]              # trail_tightness
    return np.array([f1, f2, f3, f4, f5, f6, f7, f8, f9, f10])
```

## Dependencies

```python
import numpy as np
from scipy.signal import lfilter
from scipy.optimize import minimize       # L2-logistic for model training
from v10.core.data import DataFeed
from v10.core.types import SCENARIOS
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb
```

## Estimated Runtime

- T0 (feature fix): ~5s (2 sims)
- T1 (ablation): ~10s (4 variants)
- T2 (WFO): ~30s (4 folds, 1 design)
- T3 (bootstrap): ~300s (500 paths × 2 sims each)
- T4 (monitor interaction): ~10s (4 variants)
- T5 (retrain sensitivity): ~10s (4 training windows)
- T6 (comparison): ~5s
- Total: ~6 min

## Output Files

```
x15/
  SPEC.md                    # this file
  benchmark.py               # single script, all tests T0-T6
  x15_results.json           # master results
  x15_feature_fix.csv        # T0: X14 vs X15 comparison
  x15_ablation.csv           # T1: feature subsets
  x15_wfo_results.csv        # T2: WFO fold results
  x15_bootstrap.csv          # T3: bootstrap distribution
  x15_monitor_interaction.csv # T4: filter × monitor factorial
  x15_retrain_sensitivity.csv # T5: retraining windows
  x15_comparison.csv         # T6: comprehensive table
```
