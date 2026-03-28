# Exp 11: Anti-Vol Dynamic Trail

## Status: PENDING

## Hypothesis
E5 uses fixed trail_mult = 3.0 for all market conditions.
In orderly (low vol) markets, trends are smoother → tighter trail captures more.
In chaotic (high vol) markets, wider trail avoids whipsaws.
Adapt trail_mult based on D1 volatility rank.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Feature
```
d1_rangevol84_rank365 (same as exp01/exp09)
```

## Modification to E5-ema21D1
Entry logic UNCHANGED.
Exit — dynamic trail multiplier:
```python
if d1_rangevol84_rank365[i] < low_vol_threshold:
    trail_mult = tight_mult      # e.g., 2.5 (tighter in orderly market)
else:
    trail_mult = wide_mult       # e.g., 3.5 (wider in chaotic market)
```

## Parameter sweep
- low_vol_threshold: 0.40 (fixed — below median = "orderly")
- tight_mult in [2.0, 2.5]
- wide_mult in [3.0, 3.5, 4.0]
- (6 configs)
- Also include baseline trail_mult=3.0 for reference

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, avg holding period. Delta vs baseline.

## Implementation notes
- Only the exit trail stop changes, entry is identical
- d1_rangevol84_rank365 changes slowly (D1 resolution, 84-bar + 365-bar windows)
  so trail_mult won't whipsaw intra-trade
- Trail multiplier applies to robust ATR (not standard ATR)

## Output
- Script: x39/experiments/exp11_antivol_trail.py
- Results: x39/results/exp11_results.csv

## Result
_(to be filled by experiment session)_
