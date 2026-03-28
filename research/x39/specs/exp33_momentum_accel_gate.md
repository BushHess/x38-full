# Exp 33: Momentum Acceleration Gate

## Status: PENDING

## Hypothesis
EMA spread (ema_fast - ema_slow) / ema_slow measures trend STRENGTH.
Its first derivative (rate of change) measures trend ACCELERATION.

Late-cycle entries — where the trend is still positive but decelerating —
are the most likely to hit the trail stop quickly. These are entries where
ema_spread is positive but shrinking (momentum decelerating toward crossover).

By gating entries on positive ema_spread acceleration (d(ema_spread)/dt > 0),
we filter out late-cycle entries where the crossover has already happened but
momentum is fading. This should reduce losing trades without cutting winners
that enter during genuine trend acceleration.

Mathematical motivation: the first derivative of a smoothed momentum signal
has well-known lead properties over the signal itself. If ema_spread is
analogous to MACD, ema_spread_roc is analogous to the MACD histogram —
a leading indicator of trend exhaustion.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Feature
```
ema_spread[i] = (ema_fast[i] - ema_slow[i]) / ema_slow[i]
ema_spread_roc[i] = ema_spread[i] - ema_spread[i - lookback]
```
lookback controls the smoothing of the derivative. Short lookback = noisy,
long lookback = laggy.

## Modification to E5-ema21D1
ADD acceleration gate to entry:
```python
# Original entry:
#   ema_fast > ema_slow AND vdo > 0 AND d1_regime_ok

# Modified entry:
#   ema_fast > ema_slow AND vdo > 0 AND d1_regime_ok
#   AND ema_spread_roc > min_accel

# Exit logic UNCHANGED: trail_stop OR ema_fast < ema_slow
```

## Parameter sweep
- lookback (bars for derivative): [3, 6, 12, 24]
- min_accel: [0.0, 0.001, 0.002]
  - 0.0 = just require acceleration (spread increasing)
  - 0.001 = require meaningful acceleration
  - 0.002 = require strong acceleration
- trail_mult: 3.0 (FIXED)
- (4 × 3 = 12 configs)

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, avg holding period, exposure%.
Delta vs baseline.
Also: how many entries are BLOCKED by the acceleration gate?
Win rate of blocked entries (would they have been winners or losers?).

## Implementation notes
- ema_spread_roc can be computed from the ema_spread already in compute_features()
- min_accel = 0.0 is NOT the same as no gate: it requires spread to be
  non-decreasing, which blocks entries during deceleration
- Acceleration gate may delay entries by a few bars — trade count should decrease
- If too aggressive (min_accel too high), the gate blocks good entries and
  exposure drops significantly → CAGR penalty
- Use explore.py's ema() for consistency
- Warmup: 365 days, Cost: 50 bps RT

## Output
- Script: x39/experiments/exp33_momentum_accel_gate.py
- Results: x39/results/exp33_results.csv

## Result
_(to be filled by experiment session)_
