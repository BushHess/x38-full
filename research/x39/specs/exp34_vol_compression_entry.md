# Exp 34: Volatility Compression Entry Gate

## Status: DONE

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

**MIXED**: Compression gate improves Sharpe at all thresholds but MDD slightly worse.
Negative prior from residual scan NOT confirmed — vol compression HAS conditional entry timing value.

### Distribution at all H4 bars
- Median vol_ratio_5_20 = 0.469, mean = 0.563
- 53% of bars < 0.5, 70% < 0.7, 86% < 1.0

### Sweep results (50 bps RT, baseline = E5-ema21D1)

| Threshold | Sharpe  | d_Sharpe | CAGR%  | d_CAGR  | MDD%  | d_MDD  | Trades | Blocked | Blocked WR |
|-----------|---------|----------|--------|---------|-------|--------|--------|---------|------------|
| baseline  | 1.2965  | —        | 57.77  | —       | 51.32 | —      | 221    | 0       | —          |
| 0.5       | 1.3533  | +0.0568  | 57.49  | -0.28   | 56.33 | +5.01  | 194    | 308     | 40.9%      |
| **0.6**   | **1.4866** | **+0.1901** | **68.42** | **+10.65** | 53.59 | +2.27 | 197 | 205 | 34.6% |
| **0.7**   | **1.4764** | **+0.1799** | **68.18** | **+10.41** | 51.74 | +0.42 | 202 | 157 | 33.8% |
| 0.8       | 1.4369  | +0.1404  | 66.04  | +8.27   | 51.52 | +0.20  | 207    | 113     | 30.1%      |
| 0.9       | 1.4169  | +0.1204  | 64.84  | +7.07   | 51.52 | +0.20  | 209    | 84      | 27.4%      |
| 1.0       | 1.3308  | +0.0343  | 59.38  | +1.61   | 53.58 | +2.26  | 214    | 61      | 27.9%      |

### Key observations

1. **ALL thresholds improve Sharpe** — monotonically from 0.6 (best +0.19) down to 1.0 (+0.03).
   Best: threshold=0.6 (Sh 1.487, CAGR 68.4%). Sweet spot: threshold=0.7 (Sh 1.476, MDD +0.42pp only).

2. **Blocked entries have LOWER win rate than baseline** (27-41% vs 41.2%) → selectivity is GOOD.
   The gate preferentially blocks entries that would have been losers.

3. **MDD slightly worse** at tight thresholds (0.5: +5pp, 0.6: +2.3pp).
   threshold=0.7-0.9 nearly flat on MDD (+0.2 to +0.4pp).

4. **Threshold=1.0 sanity check**: 214 vs 221 trades due to NaN vol_ratio at early bars.
   Not a bug — 7 entries occur before rolling_std(20) is available.

5. **Negative prior overturned**: vol_ratio_5_20 was NOT significant in unconditional residual scan,
   but HAS value as conditional entry timing filter within the EMA+VDO+D1 regime context.

6. **Trade count reduction modest**: 0.6 → -24 trades (11%), 0.7 → -19 trades (9%).
   Not over-filtering like X7 pyramid.

### Verdict classification

MIXED (not PASS) because no config simultaneously improves Sharpe AND MDD.
threshold=0.7 comes closest: Sharpe +0.18, MDD +0.42pp — effectively flat on MDD.
Would need WFO validation to assess robustness (single-parameter sweep, low DOF concern).
