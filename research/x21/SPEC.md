# X21: Conviction-Based Position Sizing — Entry Feature Scoring

## Context

Current system uses fixed position size f=0.30 (vol-target 15%) for ALL trades.
VDO filter is binary: enter if VDO > 0, skip otherwise. No trade is sized
differently from any other.

Prior sizing research:
- **Study #9** (position_sizing.py): Kelly, fixed-fraction, vol-targeting. Found
  f=0.30 (vol-target 15%) optimal for Calmar. But ALL trades get same f.
- **Study #11** (signal_vs_sizing.py): 5 signals × 3 sizings factorial. Confirmed
  E0 signal is best when sizing is held constant. But didn't test VARIABLE sizing.

### The Untested Idea

If entry-time observable features predict trade-level returns with IC > 0, then
Kelly-like variable sizing should improve geometric growth rate:

```
g_variable > g_fixed   when IC > 0   (Kelly theorem)
```

The churn score (X13-X14) PROVED that market-state features predict trade outcomes
at EXIT time (AUC=0.805, p=0.002). A similar model might predict outcomes at ENTRY
time.

### Why This Might Work

- VDO is continuous but used as binary (> 0 vs ≤ 0). A VDO of 0.5 signals
  stronger conviction than VDO of 0.01. Currently both get f=0.30.
- EMA spread at entry varies: tight crossover (low conviction) vs wide spread
  (strong trend). Currently both get f=0.30.
- D1 regime strength varies: barely above EMA(21d) vs far above. Currently
  both get f=0.30.

### Why This Might Fail

- Entry prediction is HARDER than exit prediction. At exit, you have trade
  context (bars held, drawdown from peak). At entry, you only have market state.
- Low number of trades (~226 over 8.5 years). Training a model on ~226 samples
  risks overfitting.
- Position sizing affects GEOMETRIC growth but NOT Sharpe ratio. If IC is small,
  the CAGR improvement may be < 2% (not worth the DOF).

## Central Question

Can entry-time observable features predict trade-level returns with sufficient
IC (information coefficient > 0.05) to justify conviction-based sizing over
fixed sizing, with ≥ 2% CAGR improvement?

## Architecture

### Phase 1: Trade-Level Return Prediction

1. Run E5+EMA1D21 on full BTC data → extract all trades
2. For each trade, record features AT ENTRY TIME:
   - `vdo_value`: continuous VDO at entry bar (currently used as binary > 0)
   - `ema_spread`: (ema_fast - ema_slow) / ema_slow at entry (trend strength)
   - `atr_pctl`: percentile of ATR within trailing 252-bar window (vol regime)
   - `d1_regime_str`: (close - ema21d) / ema21d at entry (D1 trend strength)
3. Record trade outcome: log-return = log(exit_px / entry_px) adjusted for cost
4. Train L2-penalized linear regression: outcome ~ features
5. Measure IC = rank_correlation(predicted, actual)

### Phase 2: Sizing Function

Map prediction to position size:

```python
z = (prediction - mean(predictions)) / std(predictions)
f_trade = f_base * clip(1 + beta * z, f_min/f_base, f_max/f_base)
```

- `f_base` = 0.30 (current default)
- `f_min` = 0.10 (minimum: never skip, always have skin in the game)
- `f_max` = 0.50 (maximum: bounded risk, no leverage)
- `beta` controls sizing aggression: how much to deviate from f_base

At β=0: all trades get f=0.30 (reduces to current system).
At β=1.0: z=+1 → f=0.60 (capped at 0.50), z=-1 → f=0.00 (floored at 0.10).

### Phase 3: Validation

Full pipeline: WFO, bootstrap, jackknife, PSR. Same rigor as churn filter.

### Why Only 4 Features

Same philosophy as churn filter (X14): use market-state features only.
Explicitly EXCLUDE trade-context features (bars_held, unrealized_pnl) because
they don't exist at entry time.

4 features × ~226 trades → ~56 samples per feature. Marginal but viable for
linear model with L2 regularization. Adding more features risks overfitting.

## Parameter Grid

### Tuned parameters
```
beta ∈ {0.25, 0.50, 0.75, 1.0}     — sizing aggression (4 values)
feature_set ∈ {all_4, top_2}        — all 4 features or top 2 by IC (2 values)
```

### Fixed parameters (not tuned, reduce DOF)
```
f_base = 0.30                        — current default
f_min = 0.10                         — minimum position
f_max = 0.50                         — maximum position
L2_alpha = 1.0                       — regularization (same as churn filter)
```

### Total configurations: 4 × 2 = 8

### DOF
- E5+EMA1D21 base: 4.35 (Nyholt M_eff)
- Additional: +1 (beta) = **5.35 total**
- feature_set is a model selection choice inside WFO, not an additional DOF

## Test Suite

### T-1: IC Measurement (abort gate)

Train model on full sample. Measure:
- IC = Spearman rank correlation between predicted and actual trade returns
- Per-feature IC (which features contribute?)
- Cross-validated IC (leave-20%-out, 5 folds)

**Abort gate**: If cross-validated IC < 0.05 → ABORT. Features cannot predict
trade returns, no point in sizing study.

Context: IC=0.05 on 226 trades → ~1.1 trades correctly ranked per every 20.
This is weak but potentially enough for sizing improvement.

### T0: Sizing Sweep (8 configs)

For each (beta, feature_set):
1. Train model on full sample
2. Compute per-trade sizes
3. Run backtest with variable sizing
4. Measure: Sharpe, CAGR, MDD, geometric growth rate g

**Report**: metric table for all 8 configs vs fixed f=0.30 baseline.

**Gate G0**: Best config has CAGR > baseline CAGR + 2.0 pp (minimum improvement
threshold to justify DOF).

### T1: Nested Walk-Forward Validation (4 folds)

Same fold structure as all prior studies. Each fold:
1. Train prediction model on training trades
2. For each (beta, feature_set): run sim on full data, measure training CAGR
3. Select best (beta, feature_set) by training CAGR (not Sharpe — sizing
   affects geometric growth, not risk-adjusted return)
4. Measure test CAGR and Sharpe
5. d_cagr = test_variable_cagr - test_fixed_cagr
6. d_sharpe = test_variable_sharpe - test_fixed_sharpe

**Gate G1**: win_rate ≥ 3/4 AND mean d_cagr > 0

### T2: Bootstrap (500 VCBB)

Using consensus parameters from T1.

**Gate G2**: P(d_cagr > 0) > 60%
**Gate G3**: median d_mdd ≤ +5.0 pp (variable sizing doesn't blow up MDD)

### T3: Jackknife (leave-year-out)

**Gate G4**: ≤ 2 negative folds (on d_cagr)

### T4: PSR with DOF Correction

DOF: 5.35 (E5+EMA1D21 4.35 + 1 beta)

**Gate G5**: PSR > 0.95

### T5: Comparison Table

| Strategy | Sharpe | CAGR | MDD | g (geom) | Trades | Avg f |
|----------|--------|------|-----|----------|--------|-------|
| E5+EMA1D21 (f=0.30 fixed) | ... | ... | ... | ... | ... | 0.30 |
| X21 (β=best, all_4) | ... | ... | ... | ... | ... | ... |
| X21 (β=best, top_2) | ... | ... | ... | ... | ... | ... |

Additional: distribution of per-trade f values (histogram), top/bottom 10
trades by predicted quality.

## Verdict Gates

| Gate | Test | Condition |
|------|------|-----------|
| ABORT | T-1 | IC < 0.05 → abort |
| G0 | T0 | Best CAGR > baseline + 2pp |
| G1 | T1 | WFO ≥ 75%, mean d_cagr > 0 |
| G2 | T2 | P(d_cagr > 0) > 60% |
| G3 | T2 | Median d_mdd ≤ +5pp |
| G4 | T3 | ≤ 2 negative jackknife |
| G5 | T4 | PSR > 0.95 |

## Decision Matrix

| Outcome | Action |
|---------|--------|
| IC < 0.05 (T-1) | CLOSE — entry features don't predict trade quality |
| IC ≥ 0.05, G0 fail | CLOSE — IC exists but sizing improvement < 2pp CAGR |
| All G0-G5 pass, CAGR Δ > 2pp | **PROMOTE** — conviction sizing improves geometric growth |
| All gates pass, CAGR Δ < 2pp | CLOSE — marginal, not worth DOF |
| Any gate G1-G5 fail | CLOSE — doesn't survive validation |

## Implementation Notes

### Trade feature extraction
```python
# At entry bar i:
features = {
    'vdo_value': vdo[i],                              # continuous, not binary
    'ema_spread': (ema_fast[i] - ema_slow[i]) / ema_slow[i],
    'atr_pctl': percentileofscore(atr[max(0,i-252):i+1], atr[i]) / 100,
    'd1_regime_str': (close_d1[d] - ema21d[d]) / ema21d[d],
}
# Trade return: log(exit_px / entry_px) - 2 * cps
```

### Model training
```python
from sklearn.linear_model import Ridge
model = Ridge(alpha=1.0)  # L2, same as churn filter
model.fit(X_train, y_train)
predictions = model.predict(X_test)
```

### Sizing integration
The sizing function modifies the position size in the sim loop.
NAV tracking uses actual position size (not binary in/out).
This reuses X19's fractional position machinery.

### Comparison to existing sizing studies
- Study #9 (position_sizing.py): Tests f ∈ {0.10, ..., 1.00} as FIXED.
  X21 tests f as VARIABLE per trade. Orthogonal dimension.
- Study #11 (signal_vs_sizing.py): Tests signal × fixed_sizing factorial.
  X21 tests single_signal × variable_sizing. Different question.

## Estimated Runtime

- T-1 (IC): ~2s (model fit on ~226 trades)
- T0 (sweep): ~5s (8 configs × 1 backtest)
- T1 (WFO): ~10s (4 folds × 8 configs)
- T2 (bootstrap): ~180s (500 paths, retrain model per path)
- T3 (jackknife): ~3s
- T4 (PSR): ~1s
- T5 (comparison): ~1s
- Total: ~3.5 min (if not aborted at T-1)

## Output Files

```
x21/
  SPEC.md
  benchmark.py
  x21_results.json
  x21_ic.csv              (T-1)
  x21_sweep.csv           (T0)
  x21_wfo.csv             (T1)
  x21_bootstrap.csv       (T2)
  x21_jackknife.csv       (T3)
  x21_comparison.csv      (T5)
  REPORT.md
```
