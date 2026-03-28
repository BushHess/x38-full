# Exp 05: D1 Taker Exhaustion Block

## Status: PENDING

## Hypothesis
D1 rolling taker imbalance is a REVERSAL signal (x39: negative at fwd_6, fwd_24).
Gen4 confirmed: high D1 taker buying → exhaustion → underperformance.
BLOCK entries when D1 taker imbalance is too high (buyers exhausted).

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Feature
```
d1_taker_imbal_12[i] = 2 * sum(taker_buy_base_vol, 12 D1 bars) / sum(volume, 12 D1 bars) - 1
```
Range [-1, +1]. Positive = net taker buying over last 12 days.

## Modification to E5-ema21D1
```python
# Modified: ... AND d1_taker_imbal_12 < threshold  (BLOCK when too high)
```
Exit logic UNCHANGED.

## Parameter sweep
- threshold in [0.10, 0.05, 0.02, 0.00, -0.02]
- (5 configs, note: lower = more restrictive)

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, exposure%. Delta vs baseline.

## Implementation notes
- Map D1 feature to H4 using map_d1_to_h4()
- This is a BLOCKING filter (entries blocked when value > threshold)
- The VDO entry filter already requires positive taker flow on H4 single-bar.
  This is D1 rolling 12-day aggregate — different timescale and concept.

## Output
- Script: x39/experiments/exp05_d1_taker_block.py
- Results: x39/results/exp05_results.csv

## Result
_(to be filled by experiment session)_
