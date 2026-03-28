# Exp 03: Liquidity Entry Gate

## Status: PENDING

## Hypothesis
vol_per_range (volume / price range) measures market liquidity — how much volume
is needed to move price one unit. Higher = more liquid = harder to move = more
"real" trends. x39 residual: 3/5 horizons significant, rho +0.04 to +0.14.
Gating on high liquidity should filter out entries in thin/illiquid markets.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Feature
```
range[i] = high[i] - low[i]
vol_per_range[i] = volume[i] / range[i]   # undefined if range = 0
```
Use rolling percentile to normalize (raw values scale with price level):
```
vol_per_range_pctl[i] = percentile_rank(vol_per_range[i], within trailing 168 bars)
```

## Modification to E5-ema21D1
```python
# Modified: ... AND vol_per_range_pctl > threshold
```
Exit logic UNCHANGED.

## Parameter sweep
- threshold in [0.20, 0.30, 0.40, 0.50, 0.60]
- (5 configs)

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, exposure%. Delta vs baseline.

## Implementation notes
- vol_per_range can be extreme when range ≈ 0 (doji bars). Use percentile rank to handle.
- Rolling 168-bar window for percentile rank.
- Handle division by zero: if range < 1e-10, set vol_per_range = NaN, skip bar.

## Output
- Script: x39/experiments/exp03_liquidity_gate.py
- Results: x39/results/exp03_results.csv

## Result
_(to be filled by experiment session)_
