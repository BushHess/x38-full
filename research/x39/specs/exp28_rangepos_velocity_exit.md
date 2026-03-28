# Exp 28: Rangepos Velocity Exit

## Status: PENDING

## Hypothesis
ALL 24 experiments (exp01-24) tested feature LEVELS as thresholds: "exit when
rangepos_84 < 0.25", "exit when trendq_84 < -0.10", etc. None tested feature
CHANGE RATE (velocity).

Rangepos_84 dropping from 0.80 to 0.20 in 6 bars (1 day) is a DIFFERENT signal
than slowly drifting to 0.20 over 42 bars (7 days):
- FAST drop: sudden breakdown, possibly flash crash or capitulation. Trail stop
  likely catches this anyway (large price move triggers trail).
- SLOW drift: gradual deterioration, price grinding lower within range. Trail
  stop may keep resetting higher during brief bounces. THIS is where velocity
  adds value — detecting slow deterioration that level-based exits miss.

Conversely, the KEY RISK is different: slow drifts to low rangepos might also
occur during healthy consolidation within a larger uptrend. Rangepos_84 can be
0.20 simply because the range compressed, not because the trend reversed.

This experiment tests whether RATE OF CHANGE provides useful information
beyond what level-based thresholds capture. If velocity exits are more
selective (fewer triggers, better loser targeting), they complement or
replace the level-based approach.

## Baseline
E5-ema21D1 (simplified replay): ~1.2965 Sharpe, ~51.32% MDD, 221 trades.

## Feature
```
# Rangepos level (existing):
rangepos_84[i] = (close[i] - rolling_low_84[i]) / (rolling_high_84[i] - rolling_low_84[i])

# Rangepos velocity (NEW):
# Change in rangepos over N bars. Negative = declining (bad).
delta_rp[i] = rangepos_84[i] - rangepos_84[i - N]

# N options: 6 (1 day), 12 (2 days), 24 (4 days)
```

## Modification to E5-ema21D1
Entry logic UNCHANGED.

**Part A — Velocity-only exit:**
```python
# close < trail_stop OR ema_fast < ema_slow OR delta_rp_N < velocity_threshold
# Exit when rangepos DROPS sharply (regardless of current level)
```

**Part B — Level + Velocity AND gate:**
```python
# close < trail_stop OR ema_fast < ema_slow
# OR (rangepos_84 < level_threshold AND delta_rp_N < velocity_threshold)
# Exit when rangepos is BOTH low AND declining. Double confirmation.
```

**Part C — Velocity + trendq triple AND gate:**
```python
# close < trail_stop OR ema_fast < ema_slow
# OR (delta_rp_N < velocity_threshold AND trendq_84 < tq_threshold)
# Exit when rangepos is DECLINING AND trend quality is poor. Uses velocity
# instead of level — structurally different from exp22.
```

## Parameter sweep

**Part A — Velocity-only (3 windows × 5 thresholds):**
- N in [6, 12, 24]
- velocity_threshold in [-0.40, -0.30, -0.20, -0.10, 0.00]
- (15 configs)

**Part B — Level + Velocity AND (best N from Part A × grid):**
- N = (best from Part A, or fixed N=12 as middle ground)
- level_threshold in [0.20, 0.25, 0.30]
- velocity_threshold in [-0.30, -0.20, -0.10]
- (9 configs)

**Part C — Velocity + trendq AND (best N × grid):**
- N = (best from Part A, or fixed N=12)
- velocity_threshold in [-0.30, -0.20, -0.10]
- tq_threshold in [-0.20, -0.10, 0.00]
- (9 configs)

Total: 33 configs + 1 baseline = 34 runs.

## What to measure
For each config AND baseline:
- Sharpe, CAGR%, MDD%, trade count, supplementary exit count
- Delta vs baseline for Sharpe, MDD
- Exit selectivity: % of velocity-triggered exits that are on losers

Key analysis:
1. **Velocity vs level**: compare best Part A (velocity-only) vs exp12
   (rangepos level-only at thr=0.25). Does velocity provide DIFFERENT
   information or is it redundant?

2. **Double confirmation**: does Part B (level + velocity AND) beat
   single-feature approaches? Expected: very few triggers but high
   selectivity.

3. **Velocity as trendq replacement**: does Part C (velocity + trendq)
   match or beat exp22 (level + trendq)? If yes, velocity is more
   robust because it doesn't depend on fragile L=84 level threshold.

4. **Window sensitivity**: is delta_rp robust across N=6/12/24?
   Plateau = robust mechanism. Sharp peak = another fragility.

5. **Exit timing**: when velocity exit fires, how many bars before/after
   trail stop would have fired? Velocity should catch SLOW deterioration
   that trail misses, but NOT fast crashes (trail catches those first).

## Implementation notes
- Compute rangepos_84 from explore.py's compute_features()
- delta_rp is a simple difference: rangepos_84[i] - rangepos_84[i-N]
- Handle NaN: delta_rp is NaN for first 84+N bars. No exit during warmup.
- Velocity threshold is NEGATIVE (we want drops): -0.30 means rangepos
  dropped by 0.30 units over N bars (e.g., from 0.70 to 0.40).
- Data: bars_btcusdt_2016_now_h1_4h_1d.csv
- Cost: 50 bps RT (harsh)
- Warmup: 365 days
- Run Part A first. If all velocity-only configs fail, SKIP Parts B and C
  (no point building on a dead mechanism).

## Output
- Script: x39/experiments/exp28_rangepos_velocity_exit.py
- Results: x39/results/exp28_results.csv

## Result
_(to be filled by experiment session)_
