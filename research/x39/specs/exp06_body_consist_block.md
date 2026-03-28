# Exp 06: Body Consistency Block

## Status: PENDING

## Hypothesis
body_consist_6 = sum of sign(close-open) over last 6 bars.
x39 residual: NEGATIVE at fwd_1 and fwd_6 (mean-reversion after consecutive
same-direction bars). When 5-6 consecutive bars go same direction, next bars
tend to reverse. BLOCK entry when body_consist_6 is extreme positive (6 up bars
in a row = likely pullback coming).

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Feature
```
body_sign[i] = sign(close[i] - open[i])   # +1 up, -1 down, 0 doji
body_consist_6[i] = sum(body_sign[i-5:i+1])
```
Range [-6, +6]. Value of +6 = six consecutive up bars.

## Modification to E5-ema21D1
```python
# Modified: ... AND body_consist_6 < threshold  (BLOCK entry after too many up bars)
```
Exit logic UNCHANGED.

## Parameter sweep
- threshold in [6, 5, 4, 3, 2]
- (5 configs. threshold=6 means only block after 6 consecutive up bars)

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, exposure%. Delta vs baseline.

## Implementation notes
- Simple rolling sum, no complex computation
- E5 only enters in uptrend, so body_consist_6 tends to be positive at entry anyway
- This tests whether "too bullish" short-term momentum is a contrarian signal

## Output
- Script: x39/experiments/exp06_body_consist_block.py
- Results: x39/results/exp06_results.csv

## Result
_(to be filled by experiment session)_
