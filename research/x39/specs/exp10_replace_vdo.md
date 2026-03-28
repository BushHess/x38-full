# Exp 10: Replace VDO with Trade Surprise

## Status: PENDING

## Hypothesis
VDO measures taker buy/sell imbalance (MACD-smoothed). Trade surprise measures
participation anomaly (more trades than volume predicts). Both use volume data
but capture different phenomena:
- VDO: "Are buyers or sellers more aggressive?"
- Trade surprise: "Is participation unusually high for this volume level?"

Gen4 C3 used trade surprise as its champion feature. Can it replace VDO?

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Feature
```
# Fit on first 2000 H4 bars:
log1p(num_trades) = intercept + slope * log1p(volume) + residual
raw_residual[i] = log1p(num_trades[i]) - (intercept + slope * log1p(volume[i]))
trade_surprise_168[i] = raw_residual[i] - rolling_mean(raw_residual, 168)[i]
```

## Modification to E5-ema21D1
```python
# Original: ema_fast > ema_slow AND vdo > 0            AND d1_regime_ok
# Modified: ema_fast > ema_slow AND trade_surprise_168 > threshold AND d1_regime_ok
```
Exit logic UNCHANGED.

## Parameter sweep
- threshold in [-0.05, 0.0, 0.05, 0.10, 0.15]
- (5 configs)

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, exposure%. Delta vs baseline.

## Implementation notes
- This REMOVES VDO, does NOT add on top
- num_trades exists in CSV data
- Linear regression fit is causal (first 2000 bars only)
- De-drift with rolling 168-bar mean

## Output
- Script: x39/experiments/exp10_replace_vdo.py
- Results: x39/results/exp10_results.csv

## Result
_(to be filled by experiment session)_
