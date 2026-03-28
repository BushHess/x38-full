# Exp 45: Triple Stack — Accel + Compression + Maturity Decay

## Status: DONE

## Hypothesis
Three mechanisms passed or showed promise in x39:
1. **Exp33** (accel gate): entry timing, +0.15 Sharpe, -10pp MDD
2. **Exp34** (compression gate): entry selectivity, +0.19 Sharpe, +0.4pp MDD
3. **Exp38** (maturity decay): exit protection, +0.15 Sharpe, -10pp MDD

Exp43 tests (1+3), exp44 tests (2+3). This experiment tests ALL THREE.

The risk: stacking two entry filters on top of a modified exit may
OVER-FILTER entries, dropping trade count below a useful level. X7 in
earlier research showed that pyramid filtering kills exposure. The question
is whether these two entry filters are complementary (block DIFFERENT
bad entries) or redundant (block the SAME bad entries).

If complementary: the triple stack blocks more losers than either single
gate → higher win rate AND reasonable trade count.
If redundant: trade count drops but win rate doesn't improve proportionally →
CAGR penalty from under-exposure.

## Baseline
E5-ema21D1 (simplified replay): ~1.30 Sharpe, ~197 trades.

## Components
```
# Gate 1 — Accel (exp33): blocks deceleration entries
ema_spread_roc = ema_spread[i] - ema_spread[i - 12]
accel_ok = ema_spread_roc > 0.0

# Gate 2 — Compression (exp34): blocks expanded-vol entries
compression_ok = vol_ratio_5_20[i] < compression_threshold

# Gate 3 — Maturity decay (exp38): tightens trail
effective_trail = decay(trend_age, 3.0, trail_min, decay_start, decay_end)
```

## Modification to E5-ema21D1
```python
# Entry: ALL gates must pass
#   ema_fast > ema_slow AND vdo > 0 AND d1_regime_ok
#   AND ema_spread_roc > 0.0          (gate 1)
#   AND vol_ratio_5_20 < threshold    (gate 2)

# Exit: maturity decay + standard
#   trail_stop = peak - effective_trail * robust_atr
#   exit if close < trail_stop OR ema_fast < ema_slow
```

## Parameter sweep
Fixed at best single-experiment configs for core comparison:
```
# Reference runs (4):
ref_baseline:    no gates, fixed trail=3.0
ref_accel_only:  lb=12 ma=0.0, fixed trail=3.0
ref_comp_only:   thr=0.7, fixed trail=3.0
ref_decay_only:  min=1.5 start=60 end=180, no entry gates

# Double stacks (3) — from exp43/44 for comparison:
duo_accel_decay:  lb=12 ma=0.0 + min=1.5/60/180
duo_comp_decay:   thr=0.7 + min=1.5/60/180
duo_accel_comp:   lb=12 ma=0.0 + thr=0.7, fixed trail=3.0

# Triple stacks (4):
triple_A: lb=12, ma=0.0, thr=0.6, min=1.5, start=60, end=180
triple_B: lb=12, ma=0.0, thr=0.7, min=1.5, start=60, end=180
triple_C: lb=12, ma=0.0, thr=0.7, min=2.0, start=60, end=180
triple_D: lb=12, ma=0.0, thr=0.8, min=1.5, start=60, end=180
```
(11 total: 4 refs + 3 duos + 4 triples)

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, exposure%.
Delta vs baseline for ALL configs.

Key analysis:
1. **Additivity table**: single vs duo vs triple improvements
   - Do triples beat best duo? By how much?
   - What is the marginal value of the third mechanism?
2. **Trade count**: how many entries pass BOTH gates simultaneously?
   - If trade count < 100 → risk of over-filtering (X7 trap)
3. **Overlap analysis**: what fraction of accel-blocked entries are ALSO
   compression-blocked? High overlap = redundant gates.
4. **Win rate**: does win rate increase proportionally with filtering?
   Triple win rate > duo win rate > single win rate?

## Implementation notes
- Combine all three mechanisms in one backtest loop
- Track which gates block which entries for overlap analysis
- vol_ratio_5_20 from compute_features(), ema_spread_roc computed inline,
  trend_age from compute_trend_age()
- Warmup: 365 days
- Cost: 50 bps RT

## Output
- Script: x39/experiments/exp45_triple_stack.py
- Results: x39/results/exp45_results.csv

## Result

### Summary Table (d_Sharpe vs baseline Sharpe=1.3098)

| Config | Sharpe | CAGR% | MDD% | Trades | WinRate | d_Sharpe |
|--------|--------|-------|------|--------|---------|----------|
| ref_baseline | 1.3098 | 52.70 | 41.01 | 197 | 40.6% | — |
| ref_accel_only | 1.3419 | 48.08 | 41.01 | 149 | 42.3% | +0.0321 |
| ref_comp_only | 1.4321 | 58.44 | 38.42 | 182 | 43.4% | +0.1223 |
| ref_decay_only | 1.4596 | 58.11 | 31.19 | 263 | 39.5% | +0.1498 |
| duo_accel_decay | 1.4501 | 49.75 | 37.41 | 177 | 45.8% | +0.1403 |
| duo_comp_decay | 1.5426 | 60.81 | 31.48 | 240 | 41.2% | +0.2328 |
| duo_accel_comp | 1.3584 | 48.35 | 29.69 | 140 | 44.3% | +0.0486 |
| **triple_A** | 1.3243 | 42.63 | 35.17 | 163 | 44.2% | +0.0145 |
| **triple_B** | 1.3289 | 43.14 | 34.66 | 166 | 45.8% | +0.0191 |
| **triple_C** | 1.3516 | 45.15 | 36.99 | 157 | 45.2% | +0.0418 |
| **triple_D** | 1.3865 | 46.23 | 36.90 | 170 | 47.1% | +0.0767 |

### Key findings

1. **Additivity: ALL triples REDUNDANT.** Best triple (triple_D) d_Sharpe=+0.077,
   ratio=0.252 vs sum-of-singles (+0.304). Marginal over best duo: **-0.156**.

2. **Trade count OK.** All triples >= 140 trades. No X7 trap.

3. **Overlap: MODERATE.** 27.5% of blocked entries fail BOTH gates. 45.4% fail
   accel only, 27.1% fail compression only. Gates are partially complementary
   but the accel gate's contribution is destructive when stacked.

4. **Win rate improves** (triple_D 47.1% vs baseline 40.6%) but CAGR collapses
   (-6.47pp) — accel gate removes too many profitable entries.

5. **Best duo (comp+decay) dominates.** Sharpe 1.5426, CAGR 60.81%, MDD 31.48%.
   No triple configuration comes close.

### Verdict: **TRIPLE FAILS**

The accel gate (exp33) is the weak link. It contributes the smallest single delta
(+0.032 Sharpe) and when stacked with compression, the combined entry filter
kills CAGR by removing profitable-but-decelerating entries. Compression+decay
(duo_comp_decay) is strictly superior to any triple stack.

The accel gate's benefit is subsumed by the compression gate — entries blocked by
accel that pass compression tend to be profitable. Adding accel on top of
compression destroys value.
