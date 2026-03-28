# Exp 09: Replace D1 EMA(21) Regime with D1 Anti-Vol

## Status: PENDING

## Hypothesis
E5-ema21D1 uses D1 close > D1 EMA(21) as regime filter (trend direction).
Replace with D1 anti-vol (volatility level). These measure DIFFERENT things:
- D1 EMA(21): "Is D1 trending up?"
- D1 anti-vol: "Is D1 volatility low (orderly market)?"

If anti-vol is a better regime definition than trend direction, this should improve.
If both are valuable, neither alone is optimal → combine in exp 01.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Feature
```
d1_range_pct[i] = (d1_high[i] - d1_low[i]) / d1_close[i]
d1_rangevol_84[i] = rolling_mean(d1_range_pct, 84)
d1_rangevol84_rank365[i] = percentile_rank(d1_rangevol_84[i], within trailing 365 bars)
```

## Modification to E5-ema21D1
```python
# Original: ema_fast > ema_slow AND vdo > 0 AND d1_close > d1_ema21
# Modified: ema_fast > ema_slow AND vdo > 0 AND d1_rangevol84_rank365 < threshold
```
Exit logic UNCHANGED (trail stop + EMA cross-down stay).

## Parameter sweep
- threshold in [0.30, 0.40, 0.50, 0.60, 0.70]
- (5 configs)

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, exposure%. Delta vs baseline.
Also: overlap analysis — how often do D1 EMA(21) and D1 anti-vol agree/disagree?

## Implementation notes
- D1 anti-vol rank needs 365+84 D1 bars warmup
- This REMOVES D1 EMA(21), does NOT add on top
- Map D1 feature to H4 with map_d1_to_h4()

## Output
- Script: x39/experiments/exp09_replace_d1regime.py
- Results: x39/results/exp09_results.csv

## Result
_(to be filled by experiment session)_
