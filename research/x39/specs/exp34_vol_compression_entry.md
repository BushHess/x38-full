# Exp 34: Volatility Compression Entry Gate

## Status: PENDING

## Hypothesis
vol_ratio_5_20 measures short-term volatility relative to medium-term.
Low values (compression) indicate the market is coiling — low recent movement
relative to its normal range. Compression often precedes directional breakouts.

By gating entries on vol_ratio_5_20 < threshold (compression present), we
filter out entries during already-expanded volatility where the initial move
has played out and continuation is less certain.

Mathematical motivation: volatility clustering (GARCH) implies that low-vol
periods are followed by high-vol periods. Entering during compression captures
the expansion move from the start. Entering during expansion risks entering
at the tail end of the move.

x39 residual scan: vol_ratio_5_20 was NOT significant (p > 0.05) at any horizon.
This is a NEGATIVE prior. The hypothesis is that vol_ratio_5_20 has value as an
ENTRY TIMING filter (conditional on trend being up) even if it doesn't predict
raw forward returns unconditionally. The conditioning on EMA trend + VDO may
unlock timing value that the unconditional scan misses.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Feature
```
std_5[i]  = rolling_std(close, 5)[i]
std_20[i] = rolling_std(close, 20)[i]
vol_ratio_5_20[i] = std_5[i] / std_20[i]
```
Already computed in explore.py compute_features().

## Modification to E5-ema21D1
ADD compression gate to entry:
```python
# Original entry:
#   ema_fast > ema_slow AND vdo > 0 AND d1_regime_ok

# Modified entry:
#   ema_fast > ema_slow AND vdo > 0 AND d1_regime_ok
#   AND vol_ratio_5_20 < compression_threshold

# Exit logic UNCHANGED: trail_stop OR ema_fast < ema_slow
```

## Parameter sweep
- compression_threshold: [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
  - 0.5 = very tight compression (recent vol < 50% of medium-term)
  - 1.0 = no gate (baseline equivalent, sanity check)
- trail_mult: 3.0 (FIXED)
- (6 configs)

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, avg holding period, exposure%.
Delta vs baseline.
Also: distribution of vol_ratio_5_20 at entry bars. How many entries blocked?
Median vol_ratio_5_20 at entry for baseline (to understand current distribution).

## Implementation notes
- vol_ratio_5_20 is already in compute_features() — use directly
- Very low thresholds (0.5) will block many entries → big exposure drop
- Threshold 1.0 should reproduce baseline exactly (validation check)
- The hypothesis has a negative prior (residual scan not significant) —
  this makes a positive result MORE surprising and MORE interesting
- Use explore.py helpers for consistency
- Warmup: 365 days, Cost: 50 bps RT

## Output
- Script: x39/experiments/exp34_vol_compression_entry.py
- Results: x39/results/exp34_results.csv

## Result
_(to be filled by experiment session)_
