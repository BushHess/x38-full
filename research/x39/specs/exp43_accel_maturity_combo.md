# Exp 43: Acceleration Gate + Maturity Decay Combination

## Status: PENDING

## Hypothesis
Exp33 (accel gate) and exp38 (maturity decay) both PASS full-sample with
+0.15 Sharpe. They modify INDEPENDENT parts of the strategy:
- Exp33 modifies ENTRY (blocks entries during momentum deceleration)
- Exp38 modifies EXIT (tightens trail as trend ages)

Independent mechanisms can be additive: entry timing reduces bad entries,
maturity decay protects accumulated profit. If additive, the combination
should yield +0.20 to +0.30 Sharpe over baseline. If redundant (both
capture the same improvement via different routes), the combination will
plateau near the better single mechanism.

The key test: does entry + exit jointly beat either alone?

Mathematical motivation: if entry quality and exit timing are independent
signals, the joint improvement is approximately the sum of individual
improvements. If they're correlated (both benefit the same trades),
the joint improvement is less than the sum.

## Baseline
E5-ema21D1 (simplified replay): ~1.30 Sharpe, ~197 trades.

## Components
```
# Exp33 best: entry gate
lookback = 12
min_accel = 0.0
ema_spread_roc = ema_spread[i] - ema_spread[i - 12]
entry: base_conditions AND ema_spread_roc > 0.0

# Exp38 best: exit modification
trail_min = 1.5, decay_start = 60, decay_end = 180
effective_trail decays linearly from 3.0 → 1.5 over bars 60-180 of trend age
```

## Modification to E5-ema21D1
```python
# Entry (exp33):
#   ema_fast > ema_slow AND vdo > 0 AND d1_regime_ok
#   AND ema_spread_roc > 0  (accel gate)

# Exit (exp38):
#   effective_trail = decay(trend_age, 3.0, trail_min, decay_start, decay_end)
#   trail_stop = peak - effective_trail * robust_atr
#   exit if close < trail_stop OR ema_fast < ema_slow
```

## Parameter sweep
Fixed combination of best configs:
```
# Group 1: fixed at exp33 + exp38 optima
combo_A: lb=12, ma=0.0, min=1.5, start=60, end=180

# Group 2: exp33 optimal + exp38 variants (vary exit)
combo_B: lb=12, ma=0.0, min=1.5, start=60, end=240
combo_C: lb=12, ma=0.0, min=2.0, start=60, end=180
combo_D: lb=12, ma=0.0, min=2.0, start=60, end=240

# Group 3: exp33 variant + exp38 optimal (vary entry)
combo_E: lb=6,  ma=0.0, min=1.5, start=60, end=180
combo_F: lb=24, ma=0.0, min=1.5, start=60, end=180
```
Plus: baseline, exp33-only (lb=12, ma=0.0), exp38-only (min=1.5, start=60, end=180)
(9 total: 6 combos + 3 references)

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, exposure%, avg holding period.
Delta vs baseline, delta vs exp33-only, delta vs exp38-only.

Key metric: **additivity ratio** = combo_delta / (exp33_delta + exp38_delta).
- Ratio ≈ 1.0: fully additive (independent mechanisms)
- Ratio < 0.5: redundant (same improvement, different routes)
- Ratio > 1.0: synergistic (mechanisms interact positively)

Also: how many entries pass BOTH gates? How many pass exp33 but not exp38
(or vice versa)?

## Implementation notes
- Combine exp33's entry logic with exp38's exit logic in one backtest loop
- Reuse compute_trend_age() from exp38 and ema_spread_roc from exp33
- Warmup: 365 days (use max of exp33/exp38 warmup requirements)
- Cost: 50 bps RT, INITIAL_CASH = 10_000
- exp33's warmup was only SLOW_PERIOD=120 bars; exp38 used 365 days.
  Use 365 days here for consistency with exp38's baseline numbers.

## Output
- Script: x39/experiments/exp43_accel_maturity_combo.py
- Results: x39/results/exp43_results.csv

## Result
_(to be filled by experiment session)_
