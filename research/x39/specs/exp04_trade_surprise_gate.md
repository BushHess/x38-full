# Exp 04: Trade Surprise Entry Gate

## Status: PENDING

## Hypothesis
Trade surprise = residual of num_trades vs volume (more trades than volume
predicts = unusual participation). Gen4 C3's core feature, champion strategy.
x39 residual: 2/5 horizons significant. Negative at fwd_6 (reversal),
positive at fwd_168 (continuation). As ENTRY gate: require positive surprise
= unusual participation = stronger signal quality.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Feature
```
# Fit on first 2000 H4 bars (warmup):
log1p(num_trades) = intercept + slope * log1p(volume) + residual

# For each bar:
raw_residual[i] = log1p(num_trades[i]) - (intercept + slope * log1p(volume[i]))
trade_surprise_168[i] = raw_residual[i] - rolling_mean(raw_residual, 168)[i]
```
Positive = more trades than expected (de-drifted).

## Modification to E5-ema21D1
```python
# Modified: ... AND trade_surprise_168 > threshold
```
Exit logic UNCHANGED.

## Parameter sweep
- threshold in [-0.05, 0.0, 0.05, 0.10, 0.15]
- (5 configs)

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, exposure%. Delta vs baseline.

## Implementation notes
- num_trades field exists in data CSV
- Fit linear regression on first 2000 bars ONLY (causal)
- De-drift with rolling 168-bar mean
- trade_surprise_168 has ~168 bar warmup (rolling mean)

## Output
- Script: x39/experiments/exp04_trade_surprise_gate.py
- Results: x39/results/exp04_results.csv

## Result
_(to be filled by experiment session)_
