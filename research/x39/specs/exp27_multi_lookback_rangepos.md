# Exp 27: Multi-Lookback Rangepos Consensus

## Status: DONE

## Hypothesis
Exp23 proved rangepos_84 is FRAGILE as standalone exit (L=84 sharp peak,
Sharpe range 0.1525 across lookbacks). Each lookback captures a different
timescale of "price falling within range":
- L=42 (7 days): fast, reactive, noisy (156 exits at thr=0.25)
- L=84 (14 days): sweet spot for E5 but fragile
- L=168 (28 days): slow, near-inert (8 exits at thr=0.25)

Instead of choosing one fragile lookback, aggregate multiple lookbacks
into a CONSENSUS signal. When price is low in its range at MULTIPLE
timescales simultaneously, the signal is more robust — it captures both
short-term weakness (L=42) AND medium-term structural decline (L=168).

Three aggregation methods:
- **MIN**: min(rangepos_42, rangepos_84, rangepos_168). Most conservative —
  requires price low at ALL timescales. Fewest triggers but highest confidence.
- **MEAN**: average across lookbacks. Moderate smoothing.
- **WEIGHTED**: emphasize medium lookback: 0.25×rp_42 + 0.50×rp_84 + 0.25×rp_168.
  Anchored on L=84 but stabilized by neighbors.

If multi-lookback consensus is more robust than single-L, it provides a better
foundation for the AND gate (exp22 → improved AND gate).

## Baseline
E5-ema21D1 (simplified replay): ~1.2965 Sharpe, ~51.32% MDD, 221 trades.

## Features
```
# Three rangepos at different lookbacks:
rangepos_42[i]  = (close[i] - min_42) / (max_42 - min_42)     # 7-day
rangepos_84[i]  = (close[i] - min_84) / (max_84 - min_84)     # 14-day
rangepos_168[i] = (close[i] - min_168) / (max_168 - min_168)   # 28-day

# Aggregation methods:
rp_min[i]  = min(rangepos_42[i], rangepos_84[i], rangepos_168[i])
rp_mean[i] = (rangepos_42[i] + rangepos_84[i] + rangepos_168[i]) / 3
rp_wt[i]   = 0.25 * rangepos_42[i] + 0.50 * rangepos_84[i] + 0.25 * rangepos_168[i]

# Trendq for AND gate variant:
trendq_84[i] = ret_84[i] / realized_vol_84[i]
```

## Modification to E5-ema21D1
Entry logic UNCHANGED.

**Part A — Multi-lookback standalone exit:**
```python
# close < trail_stop OR ema_fast < ema_slow OR rp_agg < threshold
```

**Part B — Multi-lookback AND gate:**
```python
# close < trail_stop OR ema_fast < ema_slow
# OR (rp_agg < rp_threshold AND trendq_84 < tq_threshold)
```
Where rp_agg is one of {rp_min, rp_mean, rp_wt}.

## Parameter sweep

**Part A — Standalone (3 aggregations × 5 thresholds):**
- aggregation in [min, mean, weighted]
- threshold in [0.15, 0.20, 0.25, 0.30, 0.35]
- Also: single L=84 at same thresholds (exp12 reproduction)
- Total: 15 + 5 = 20 configs

**Part B — AND gate (3 aggregations × 3 thresholds):**
- aggregation in [min, mean, weighted]
- rp_threshold in [0.15, 0.20, 0.25]
- tq_threshold = -0.10 (fixed, exp22 optimum)
- Also: single L=84 AND gate at same thresholds (exp22 reproduction)
- Total: 9 + 3 = 12 configs

Grand total: 32 configs + 1 baseline = 33 runs.

## What to measure
For each config AND baseline:
- Sharpe, CAGR%, MDD%, trade count, supplementary exit count
- Delta vs baseline for Sharpe, MDD

Key analysis:
1. **Robustness comparison**: For each aggregation, compute Sharpe range
   across thresholds [0.15-0.35]. Compare with single L=84.
   - Lower range = more robust to threshold choice.
   - Target: range < 0.05 (plateau).

2. **Best performance comparison**: does any multi-lookback config match or
   beat single L=84 performance?
   - Part A: multi-lookback best vs exp12 (rp_84 thr=0.25, +0.046 Sharpe)
   - Part B: multi-lookback AND best vs exp22 (rp_84=0.20, tq=-0.10, +0.057 Sharpe)

3. **Exit count profile**: multi-lookback should have DIFFERENT exit count vs
   single-L at same threshold. MIN aggregation should trigger less (all
   timescales must agree). MEAN should smooth.

4. **Trade overlap**: of exits triggered by multi-lookback, which also
   triggered by single L=84? High overlap + similar performance = no value
   added. Low overlap + better performance = genuine robustness gain.

## Implementation notes
- Compute all three rangepos lookbacks (42, 84, 168) using pandas rolling
- For MIN aggregation: handle NaN carefully — if any lookback is NaN, result
  is NaN → no exit trigger during warmup
- rangepos_168 needs 168 bars of warmup. All three lookbacks available only
  after bar 168. Before that: fall back to available lookbacks only, or skip
  (use skip for cleanliness).
- Data: bars_btcusdt_2016_now_h1_4h_1d.csv
- Cost: 50 bps RT (harsh)
- Warmup: 365 days

## Output
- Script: x39/experiments/exp27_multi_lookback_rangepos.py
- Results: x39/results/exp27_results.csv

## Result

**33 runs completed. Baseline: Sharpe 1.2965, CAGR 57.77%, MDD 51.32%, 221 trades.**

### Part A — Standalone exit

| Config | Sharpe | d_Sharpe | MDD% | d_MDD | Trades | Supp exits |
|--------|--------|----------|------|-------|--------|------------|
| L84 thr=0.25 (best L84) | 1.3427 | +0.0462 | 44.95 | -6.37 | 240 | 35 |
| mean thr=0.35 (best multi) | 1.3686 | +0.0721 | 49.94 | -1.38 | 249 | 56 |
| weighted thr=0.30 | 1.3612 | +0.0647 | 48.55 | -2.77 | 238 | 35 |
| weighted thr=0.25 | 1.3339 | +0.0374 | 46.34 | -4.98 | 231 | 21 |

**Robustness (Sharpe range across thresholds 0.15-0.35):**
- L=84 single: 0.0868 [1.2559 - 1.3427]
- MIN: 0.3286 [0.9736 - 1.3022] — WORST, over-triggers massively
- MEAN: 0.0855 [1.2831 - 1.3686] — similar to L=84
- WEIGHTED: 0.0668 [1.2944 - 1.3612] — BEST robustness, closest to plateau target

No aggregation achieves the target range < 0.05.

### Part B — AND gate (tq_threshold = -0.10 fixed)

| Config | Sharpe | d_Sharpe | MDD% | d_MDD | Trades | Supp exits | Selectivity |
|--------|--------|----------|------|-------|--------|------------|-------------|
| L84 AND rp=0.20 (best L84) | 1.3534 | +0.0569 | 44.24 | -7.08 | 223 | 12 | 83.3% |
| min AND rp=0.20 (best multi) | 1.3579 | +0.0614 | 48.74 | -2.58 | 238 | 33 | 87.9% |
| weighted AND rp=0.25 | 1.3454 | +0.0489 | 45.83 | -5.49 | 226 | 16 | 93.8% |

### Key findings

1. **Robustness**: WEIGHTED is most robust (range 0.0668) but still above 0.05 target.
   MIN is catastrophic (range 0.3286) — over-triggers at higher thresholds.
   MEAN similar to single L=84 (0.0855 vs 0.0868).

2. **Performance**: Multi-lookback BEATS single L=84 on Sharpe delta
   (mean_thr=0.35: +0.0721 vs L84_thr=0.25: +0.0462).
   BUT L=84 wins decisively on MDD (-6.37 pp vs -1.38 pp).
   **Tradeoff, not strict improvement.**

3. **Exit count**: MIN over-triggers (67-302 supp exits vs L84's 9-95).
   MEAN/WEIGHTED are conservative (2-66 exits). MIN is too aggressive.

4. **Overlap**: MEAN/WEIGHTED are ~80-100% overlap with L=84 — they are
   effectively smoothed versions of L=84, not genuinely different signals.
   MIN is only ~10-26% overlap — genuinely different but destructive.

5. **AND gate**: L84_AND_rp=0.20 remains the best MDD improvement (-7.08 pp)
   with strong Sharpe (+0.0569). Multi-lookback AND doesn't beat it on MDD.

### Verdict

**MIXED**: Multi-lookback consensus provides marginally better Sharpe than single
L=84 (best: mean_thr=0.35 +0.0721 vs +0.0462), but at the cost of much smaller
MDD improvement (-1.38 pp vs -6.37 pp). The hypothesis that multi-lookback would
be MORE ROBUST is partially confirmed for WEIGHTED (range 0.0668 < L84's 0.0868)
but none achieve the 0.05 plateau target. MEAN/WEIGHTED are high-overlap with L=84
(not genuinely new information). MIN captures different exits but destroys
performance. Single L=84 remains the better practical choice for MDD reduction.
