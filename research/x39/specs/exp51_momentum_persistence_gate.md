# Exp 51: Momentum Persistence Entry Gate

## Status: PENDING

## Hypothesis
Exp33 (accel gate) tested momentum ACCELERATION — the rate of change of
ema_spread. It failed WFO because acceleration is regime-dependent:
bull markets have sustained acceleration that the gate blocks.

This experiment tests a DIFFERENT momentum property: PERSISTENCE.
Instead of "is momentum increasing right now?", ask "has momentum been
consistently positive recently?"

ret_168 > 0 for at least K of the last M bars = persistent upward momentum.
This captures trend QUALITY — a trend where momentum has been reliably
positive is higher quality than one with intermittent momentum.

The key difference from accel gate: persistence is NOT regime-dependent
in the same way. Bull markets have HIGH persistence (ret_168 consistently
positive). Bear markets have LOW persistence. The gate naturally adapts:
it's permissive in bull (most entries pass) and restrictive in bear
(many entries blocked). This is the OPPOSITE of the accel gate's failure
mode (blocks good bull entries).

Mathematical motivation: persistence of a trend signal is a measure of
trend RELIABILITY, not strength. A persistent signal has lower reversal
probability per bar. This is related to the Hurst exponent — persistent
series (H > 0.5) have predictable continuations.

Connection to residual scan: ret_168 has 4/5 significant horizons
(strongest after d1_rangevol84_rank365). Its persistence property has
not been tested as an entry filter.

## Baseline
E5-ema21D1 (simplified replay): ~1.30 Sharpe, ~197 trades, WR ~40.6%.

## Feature
```python
# ret_168 > 0 over trailing M bars: how many are positive?
ret_168_positive[i] = 1 if ret_168[i] > 0 else 0
persistence[i] = sum(ret_168_positive[i-M+1:i+1]) / M

# Gate: persistence >= K/M
# K/M = 0.5 → majority of recent M bars had positive 28-day return
# K/M = 0.8 → strongly persistent momentum
```

## Modification to E5-ema21D1
ADD persistence gate to entry:
```python
# Original entry:
#   ema_fast > ema_slow AND vdo > 0 AND d1_regime_ok

# Modified entry:
#   ema_fast > ema_slow AND vdo > 0 AND d1_regime_ok
#   AND persistence >= min_persistence

# Exit logic UNCHANGED: trail_stop OR ema_fast < ema_slow
```

## Parameter sweep
- M (lookback window, H4 bars): [42, 84, 168]
  - 42 = 7 days of persistence history
  - 84 = 14 days
  - 168 = 28 days (same horizon as ret_168 itself)
- min_persistence: [0.5, 0.6, 0.7, 0.8]
  - 0.5 = majority positive
  - 0.8 = strongly persistent
- (3 × 4 = 12 configs)

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, exposure%.
Delta vs baseline.

Key analysis:
1. **Selectivity**: blocked WR vs baseline WR. Is the gate SELECTIVE?
2. **Regime behavior**: persistence at entry bars per WFO window.
   In bull windows: what fraction of entries pass? (should be high)
   In bear windows: what fraction blocked? (should be high)
3. **Complementarity with vol compression**: overlap analysis.
   What fraction of persistence-blocked entries are ALSO compression-blocked?
   Low overlap → potentially stackable with vol compression.

## Implementation notes
- ret_168 is already in compute_features() — use directly
- persistence[i] requires M+168 bars of history → within 365-day warmup for all M
- The gate is naturally regime-adaptive: bull→permissive, bear→restrictive.
  This is BY DESIGN, not a flaw (unlike accel gate which was regime-DEstructive)
- If persistence is selective AND complementary with vol compression,
  a follow-up stacking experiment may be warranted
- Warmup: 365 days, Cost: 50 bps RT

## Output
- Script: x39/experiments/exp51_momentum_persistence_gate.py
- Results: x39/results/exp51_results.csv

## Result
_(to be filled by experiment session)_
