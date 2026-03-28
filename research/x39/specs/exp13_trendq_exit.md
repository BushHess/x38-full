# Exp 13: Trend Quality Exit

## Status: PENDING

## Hypothesis
trendq_84 = ret_84 / realized_vol_84. When trendq drops to zero or negative,
momentum has stalled relative to volatility — trend is degrading.
Use as EXIT signal instead of (or in addition to) EMA cross-down.

Advantage over EMA cross-down: trendq responds to volatility expansion
(denominator), not just price direction. A trend can still be "up" on EMA
but "degraded" on trendq if volatility spikes.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Feature
```
log_ret[i] = log(close[i] / close[i-1])
realized_vol_84[i] = std(log_ret[i-83:i+1]) * sqrt(84)
ret_84[i] = close[i] / close[i-84] - 1
trendq_84[i] = ret_84[i] / realized_vol_84[i]
```

## Modification to E5-ema21D1
Entry logic UNCHANGED.
Exit — REPLACE EMA cross-down with trendq. Trail stop KEPT:
```python
# Original: close < trail_stop OR ema_fast < ema_slow
# Modified: close < trail_stop OR trendq_84 < threshold
# trail_stop = peak - 3.0 * robust_atr  (KEPT, unchanged from E5)
# EMA cross-down is REMOVED, replaced by trendq_84 < threshold
```

## Parameter sweep
- threshold in [-0.2, -0.1, 0.0, 0.1, 0.2]
- (5 configs)

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, avg holding period. Delta vs baseline.

## Implementation notes
- This REPLACES EMA cross-down exit, not adds to it
- trendq can be negative even when EMA fast > slow (if recent vol spike)
- Trail stop is KEPT regardless

## Output
- Script: x39/experiments/exp13_trendq_exit.py
- Results: x39/results/exp13_results.csv

## Result
_(to be filled by experiment session)_
