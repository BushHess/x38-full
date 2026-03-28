# Exp 08: Replace EMA Crossover with rangepos_168

## Status: PENDING

## Hypothesis
rangepos_168 = where price sits in its 168-bar high-low range [0,1].
Gen4's strongest continuation signal (t=12.54). Instead of "fast EMA > slow EMA",
use "price is in upper half of recent range" as trend definition.
Conceptually different: EMA measures direction of momentum, rangepos measures
position within range.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Feature
```
rolling_high_168[i] = max(high[i-167:i+1])
rolling_low_168[i]  = min(low[i-167:i+1])
rangepos_168[i] = (close[i] - rolling_low_168[i]) / (rolling_high_168[i] - rolling_low_168[i])
```

## Modification to E5-ema21D1
```python
# Original entry: ema_fast > ema_slow AND vdo > 0 AND d1_regime_ok
# Modified entry: rangepos_168 > entry_thresh AND vdo > 0 AND d1_regime_ok

# Original exit:  close < trail_stop OR ema_fast < ema_slow
# Modified exit:  close < trail_stop OR rangepos_168 < exit_thresh
```
Hysteresis: entry threshold > exit threshold (avoid whipsawing).

## Parameter sweep
- entry_thresh in [0.50, 0.55, 0.65]
- exit_thresh in [0.30, 0.40]
- (6 configs)

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, exposure%. Delta vs baseline.

## Implementation notes
- rangepos_168 is naturally bounded [0,1], no normalization needed
- Gen4 C1 used rangepos with hysteresis (entry > exit threshold) — follow same pattern
- rolling high/low uses pd.Series.rolling(168).max()/.min()

## Output
- Script: x39/experiments/exp08_replace_ema_rangepos.py
- Results: x39/results/exp08_results.csv

## Result
_(to be filled by experiment session)_
