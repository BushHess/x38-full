# Exp 50: Alternative Compression Measures — Mechanism Robustness

## Status: PENDING

## Hypothesis
vol_ratio_5_20 (std_5 / std_20) is the only WFO-validated entry filter.
Is the MECHANISM (volatility compression → better entries) robust, or is
vol_ratio_5_20 a lucky feature?

If multiple independent compression measures produce similar selectivity
and performance → the mechanism is robust (compression genuinely predicts
entry quality). If ONLY vol_ratio_5_20 works → potential overfit to a
specific feature, and the WFO result should be treated with more caution.

This is a ROBUSTNESS test, not a search for a better feature. The bar is:
do alternative compression measures show SELECTIVITY (blocked WR < baseline WR)?

## Baseline
E5-ema21D1 (simplified replay): ~1.30 Sharpe, ~197 trades, WR ~40.6%.

## Alternative compression measures

All measure "short-term variability relative to medium-term":

```python
# 1. Original: vol_ratio_5_20 (std-based, on close prices)
vol_ratio_5_20 = rolling_std(close, 5) / rolling_std(close, 20)

# 2. ATR compression (range-based, not close-based)
#    Uses true range instead of close-to-close std
atr_5 = simple_moving_avg(true_range, 5)
atr_20 = simple_moving_avg(true_range, 20)
atr_ratio_5_20 = atr_5 / atr_20

# 3. Range compression (high-low range ratio)
range_5 = rolling_mean(high - low, 5)
range_20 = rolling_mean(high - low, 20)
range_ratio_5_20 = range_5 / range_20

# 4. Bollinger width percentile (normalized volatility)
bb_width = rolling_std(close, 20) / rolling_mean(close, 20)
bb_pctl = percentile_rank(bb_width, trailing 100 bars)

# 5. Wider window: vol_ratio_5_50
vol_ratio_5_50 = rolling_std(close, 5) / rolling_std(close, 50)
```

## Procedure

For EACH compression measure:
1. Compute the measure for all H4 bars
2. At baseline entry bars, record measure value
3. Test gate: measure < threshold, for threshold in [P25, P33, P50, P67]
   of the measure's distribution at entry bars
4. Run full backtest at threshold ≈ 0.6-equivalent (matched to block ~30% entries)
5. Compute: Sharpe, d_Sharpe, blocked WR, selectivity_score

## What to measure

| Measure | Sharpe | d_Sharpe | Blocked WR | Selective? | Correlation with vol_ratio_5_20 |
|---------|--------|----------|------------|------------|-------------------------------|

Key analysis:
1. **How many measures are selective?** (blocked WR < baseline WR)
   - All 5 selective → mechanism is robust
   - Only vol_ratio_5_20 → feature-specific
2. **Correlation between measures**: if all measures are highly correlated
   (r > 0.9), they're functionally identical. If diverse (r < 0.7),
   each captures different compression aspects.
3. **Performance similarity**: do selective measures produce similar
   Sharpe improvement to vol_ratio_5_20?

## Pass criteria
- **MECHANISM ROBUST** if ≥ 3/5 alternative measures are selective
- **MECHANISM FRAGILE** if only vol_ratio_5_20 (or 1 other) is selective

## Implementation notes
- Compute all 5 measures in addition to vol_ratio_5_20 (already in features)
- atr_5/atr_20 use simple MA of true range (NOT robust_atr — that has capping)
- bb_pctl needs 100-bar trailing window → trivial warmup
- Match blocking rate (~30% of entries) across measures for fair comparison
  rather than using a fixed threshold value
- Warmup: 365 days, Cost: 50 bps RT

## Output
- Script: x39/experiments/exp50_alt_compression_measures.py
- Results: x39/results/exp50_results.csv

## Result
_(to be filled by experiment session)_
