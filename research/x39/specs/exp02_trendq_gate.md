# Exp 02: Trend Quality Entry Gate

## Status: PENDING

## Hypothesis
Trend quality (momentum / realized volatility) predicts continuation at
medium-long horizons (x39 residual: 3/5 horizons, rho +0.027 to +0.117).
High trendq = clean, efficient trend. Low trendq = choppy momentum.
Gating entries on trendq_84 should skip entries in noisy trends.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Feature
```
log_ret[i] = log(close[i] / close[i-1])
realized_vol_84[i] = std(log_ret[i-83:i+1]) * sqrt(84)
ret_84[i] = close[i] / close[i-84] - 1
trendq_84[i] = ret_84[i] / realized_vol_84[i]
```
High trendq = strong momentum relative to noise.

## Modification to E5-ema21D1
```python
# Original: ema_fast > ema_slow AND vdo > 0 AND d1_regime_ok
# Modified: ... AND trendq_84 > threshold
```
Exit logic UNCHANGED.

## Parameter sweep
- threshold in [0.0, 0.2, 0.4, 0.6, 0.8]
- (5 configs)

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, exposure%. Delta vs baseline.

## Implementation notes
- Compute on H4 close array
- realized_vol_84 needs 84 bars warmup
- trendq_84 can be negative (downtrend) or positive (uptrend)
- Since E5 only enters in uptrend (ema_fast > ema_slow), trendq will usually be positive at entry

## Output
- Script: x39/experiments/exp02_trendq_gate.py
- Results: x39/results/exp02_results.csv

## Result
_(to be filled by experiment session)_
