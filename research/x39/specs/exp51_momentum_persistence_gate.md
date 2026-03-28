# Exp 51: Momentum Persistence Entry Gate

## Status: DONE — FAIL

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

**Verdict: FAIL** — No config improves Sharpe over baseline. Gate is NOT selective.

### Best config
M=42, min_pers=0.7: Sharpe 1.2983 (+0.0018), CAGR 52.79% (-4.98 pp), MDD 52.79% (+1.47 pp).
Delta is noise-level (+0.0018 Sharpe). CAGR drops substantially in all configs.

### Key findings

1. **NOT selective (0/12 configs)**: All blocked entry pools have WR >= baseline WR (41.2%).
   At M=84, blocked WR reaches 46-47% — the gate blocks WINNERS more than losers.

2. **Redundant with D1 EMA(21) regime filter**: Entry bars already have very high persistence
   (median 0.93-0.98 for M=42/84). When d1_regime_ok=True, ret_168 is almost always
   persistently positive. The gate adds no new information beyond what d1_regime_ok provides.

3. **Longer lookbacks = worse**: M=84 and M=168 destroy alpha (Sharpe drops 0.13-0.24)
   because they block entries during regime transitions that are actually profitable.

4. **Low vol-compression overlap (26-32%)**: Persistence and vol compression target different
   entries. However, since persistence itself has no value, overlap is moot.

5. **One config barely MDD-improves**: M=168, min_pers=0.6 has MDD 47.48% (-3.84 pp) but
   Sharpe 1.1297 (-0.17). Not a tradeoff worth pursuing.

### Why the hypothesis was wrong
The hypothesis predicted persistence would be regime-adaptive (permissive in bull, restrictive
in bear). This IS true — but the existing D1 EMA(21) filter already captures this property.
ret_168 persistence is collinear with d1_regime_ok. The gate is redundant, not complementary.

### Baseline
Sharpe 1.2965, CAGR 57.77%, MDD 51.32%, 221 trades, WR 41.2%, exposure 43.0%.
