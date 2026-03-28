# Exp 23: Rangepos Lookback Robustness

## Status: PENDING

## Hypothesis
Exp12 used rangepos_84 with threshold 0.25 as supplementary exit and achieved
+0.046 Sharpe, −6.37 pp MDD. But why 84 bars specifically?

The 84-bar lookback (= 14 days on H4) was inherited from the Gen4 research
where rangepos_84 showed the strongest continuation signal (t=12.54). However,
that was for ENTRY prediction. For EXIT timing, the optimal lookback could be
different — shorter lookbacks react faster (catching drops sooner but more noise),
longer lookbacks are smoother (fewer false alarms but slower to react).

This experiment tests exp12's rangepos exit across multiple lookback windows
to determine:
1. Is 84 optimal or was it arbitrary? (local peak vs plateau)
2. If a plateau exists across lookbacks → the mechanism is robust
3. If 84 is a sharp peak → the mechanism is fragile / overfit to that window

This is a ROBUSTNESS CHECK, not a new mechanism. It validates the foundation
before exp19/exp20/exp22 build on rangepos.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Feature
```
# Parameterized lookback:
rolling_high_L[i] = max(high[i-L+1:i+1])
rolling_low_L[i]  = min(low[i-L+1:i+1])
rangepos_L[i] = (close[i] - rolling_low_L[i]) / (rolling_high_L[i] - rolling_low_L[i])

# L values to test:
# 42  = 7 days  (fast, responsive)
# 63  = 10.5 days
# 84  = 14 days (exp12 value)
# 126 = 21 days
# 168 = 28 days (slow, smooth)
```

## Modification to E5-ema21D1
Entry logic UNCHANGED.
Exit — ADD rangepos_L condition (same as exp12, varying L):
```python
# Original: close < trail_stop OR ema_fast < ema_slow
# Modified: close < trail_stop OR ema_fast < ema_slow OR rangepos_L < threshold
```

## Parameter sweep
Two-dimensional sweep: lookback × threshold.

- lookback L in [42, 63, 84, 126, 168]
- threshold in [0.15, 0.20, 0.25, 0.30]

Total: 5 × 4 = 20 configs + 1 baseline = 21 runs.

Note: L=84, threshold=0.25 is the exp12 optimum — results should reproduce.

## What to measure
For each config AND baseline:
- Sharpe, CAGR%, MDD%, trade count, win rate, exposure%
- Delta vs baseline for Sharpe, CAGR, MDD
- Exit count triggered by rangepos (how reactive is each lookback?)

Key analysis (AFTER collecting all results):
1. **Lookback sensitivity**: at fixed threshold=0.25, plot Sharpe vs L.
   - Plateau (L=63-126 similar) → robust mechanism
   - Sharp peak at L=84 → fragile, possibly overfit
2. **Threshold sensitivity per lookback**: does optimal threshold shift with L?
   - Shorter L → lower threshold needed (more volatile rangepos)
   - If threshold scales predictably with L → systematic relationship
3. **Best overall config**: which (L, threshold) pair maximizes Sharpe?
   Does it differ from (84, 0.25)?

## Implementation notes
- Compute rangepos for each lookback separately (not from explore.py which
  only computes L=84 and L=168). Add L=42, 63, 126 on the fly.
- rolling_high and rolling_low use pandas rolling or manual loop
- For L=42 and L=63, rangepos will be more volatile — expect more exit triggers
  and potentially more churn (lower threshold may be needed to compensate)
- Data: bars_btcusdt_2016_now_h1_4h_1d.csv
- Cost: 50 bps RT (harsh)
- Warmup: 365 days

## Output
- Script: x39/experiments/exp23_rangepos_lookback_robustness.py
- Results: x39/results/exp23_results.csv

## Result
_(to be filled by experiment session)_
