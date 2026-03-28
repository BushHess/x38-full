# Exp 35: D1 EMA Slope Confirmation

## Status: PENDING

## Hypothesis
Current D1 regime filter is binary: close > D1 EMA(21) → regime OK.
This allows entries when price is above the EMA but the EMA itself is
DECLINING (late bear → early recovery, or false breakout above declining EMA).

Adding a slope requirement — D1 EMA must be RISING — filters entries where
the daily trend structure is still bearish even though price has temporarily
crossed above. A rising EMA confirms that the underlying trend has shifted,
not just that price spiked.

Mathematical motivation: the EMA is a low-pass filter. Its slope represents
the filtered trend direction. Requiring positive slope means the trend has
genuinely turned, not just that price crossed a declining moving average.
This is a second-order confirmation (direction of the direction indicator).

Connection to D1 EMA proven component: D1 EMA(21) regime is one of the
4 PROVEN components (p=1.5e-5, 16/16 ALL metrics). Adding slope to the
proven filter tests whether the binary version leaves value on the table.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Feature
```
d1_ema21[i]       = ema(d1_close, 21)[i]
d1_ema_slope[i]   = (d1_ema21[i] - d1_ema21[i - slope_lookback]) / d1_ema21[i - slope_lookback]
d1_slope_ok[i]    = d1_ema_slope[i] > min_slope
```
slope_lookback controls how many D1 bars to look back for slope computation.
min_slope controls how steep the rise must be.

## Modification to E5-ema21D1
ADD slope requirement to D1 regime filter:
```python
# Original entry:
#   ema_fast > ema_slow AND vdo > 0 AND d1_regime_ok
#   where d1_regime_ok = d1_close > d1_ema21

# Modified entry:
#   ema_fast > ema_slow AND vdo > 0 AND d1_regime_ok AND d1_slope_ok
#   where d1_regime_ok = d1_close > d1_ema21   (unchanged)
#         d1_slope_ok  = d1_ema_slope > min_slope  (NEW)

# Exit logic UNCHANGED: trail_stop OR ema_fast < ema_slow
```

## Parameter sweep
- slope_lookback (D1 bars): [3, 5, 10, 15]
  - 3 = 3-day slope (responsive, noisy)
  - 15 = 15-day slope (smooth, laggy)
- min_slope: [0.0, 0.001, 0.005, 0.01]
  - 0.0 = just require non-declining EMA
  - 0.001 = ~0.1% rise over lookback period
  - 0.01 = ~1% rise over lookback period (aggressive)
- trail_mult: 3.0 (FIXED)
- (4 × 4 = 16 configs)

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, avg holding period, exposure%.
Delta vs baseline.
Also: how many entries are blocked by slope requirement? D1 EMA slope
distribution at baseline entry bars. Entry delay (bars between d1_regime_ok
and d1_slope_ok becoming true simultaneously).

## Implementation notes
- D1 EMA slope must be computed on D1 bars then mapped to H4 grid
  using map_d1_to_h4() — same causal alignment as d1_regime_ok
- slope_lookback refers to D1 bars, NOT H4 bars
- d1_ema_slope[i] requires slope_lookback prior D1 bars — additional warmup
- Very high min_slope (0.01) with long lookback (15) is very restrictive:
  requires 1% EMA rise over 15 days, which only happens in strong trends
- Use explore.py helpers for consistency
- Warmup: 365 days, Cost: 50 bps RT

## Output
- Script: x39/experiments/exp35_d1_ema_slope.py
- Results: x39/results/exp35_results.csv

## Result
_(to be filled by experiment session)_
