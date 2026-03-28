# Exp 12: Range Position Exit

## Status: PENDING

## Hypothesis
rangepos_84 has NEGATIVE residual correlation at short horizons (fwd_1: -0.023,
fwd_6: -0.031). When price is near top of 84-bar range, short-term pullback
is more likely. Use rangepos_84 dropping below threshold as supplementary exit.

This is DIFFERENT from trail stop: trail stop triggers on absolute price decline
from peak. rangepos exit triggers on price falling within its recent range,
regardless of how far from peak.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Feature
```
rolling_high_84[i] = max(high[i-83:i+1])
rolling_low_84[i]  = min(low[i-83:i+1])
rangepos_84[i] = (close[i] - rolling_low_84[i]) / (rolling_high_84[i] - rolling_low_84[i])
```

## Modification to E5-ema21D1
Entry logic UNCHANGED.
Exit — ADD rangepos condition:
```python
# Original: close < trail_stop OR ema_fast < ema_slow
# Modified: close < trail_stop OR ema_fast < ema_slow OR rangepos_84 < threshold
```

## Parameter sweep
- threshold in [0.15, 0.20, 0.25, 0.30, 0.35]
- trail_mult: 3.0 (FIXED, same as E5 baseline — this experiment only ADDS rangepos exit)
- (5 configs)

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, avg holding period. Delta vs baseline.
Also: how many exits triggered by rangepos vs trail vs trend?

## Implementation notes
- rangepos_84 can drop sharply during a trend reversal — may exit BEFORE trail stop
- This adds an ADDITIONAL exit, not a replacement
- Could reduce drawdowns but also cut winners short

## Output
- Script: x39/experiments/exp12_rangepos_exit.py
- Results: x39/results/exp12_results.csv

## Result
_(to be filled by experiment session)_
