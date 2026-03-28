# Exp 27: Multi-Lookback Rangepos Consensus

## Status: PENDING

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
_(to be filled by experiment session)_
