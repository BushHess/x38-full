# Exp 07: Replace EMA Crossover with ret_168

## Status: PENDING

## Hypothesis
Gen1 V6's frozen winner uses ret_168 > 0 as its ENTIRE entry signal.
x39 residual: 4/5 horizons significant, independent of EMA regime.
If ret_168 carries momentum information BEYOND EMA crossover, it might
work as a SIMPLER replacement. One quantity instead of two EMAs.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Feature
```
ret_168[i] = close[i] / close[i-168] - 1
```
168 H4 bars = 28 days. Positive = price higher than 28 days ago.

## Modification to E5-ema21D1
REPLACE entry trend condition:
```python
# Original entry: ema_fast > ema_slow AND vdo > 0 AND d1_regime_ok
# Modified entry: ret_168 > 0         AND vdo > 0 AND d1_regime_ok

# Original exit:  close < trail_stop OR ema_fast < ema_slow
# Modified exit:  close < trail_stop OR ret_168 < exit_threshold
```

## Complete entry/exit logic
```python
# Entry: ret_168 > 0 AND vdo > 0 AND d1_regime_ok
# Exit:  close < trail_stop OR ret_168 < exit_threshold
#        trail_stop = peak - 3.0 * robust_atr  (KEPT, unchanged from E5)
#        EMA cross-down is REMOVED, replaced by ret_168 < exit_threshold
```

## Parameter sweep
- entry_threshold: 0 (fixed, same as gen1 V6)
- exit_threshold in [-0.05, -0.02, 0.0, 0.02, 0.05]
- trail_mult: 3.0 (fixed, same as E5 baseline)
- (5 configs for exit sensitivity)

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, exposure%. Delta vs baseline.

## Implementation notes
- ret_168 needs 168 bars warmup
- Exit threshold matters: ret_168 < 0 means price below 28 days ago.
  Using -0.05 = stay in until price is 5% below 28-day-ago level (generous).
  Using 0.05 = exit when price stops being 5% above (aggressive).
- Robust ATR trail stop is KEPT (only trend exit is replaced)

## Output
- Script: x39/experiments/exp07_replace_ema_ret168.py
- Results: x39/results/exp07_results.csv

## Result
_(to be filled by experiment session)_
