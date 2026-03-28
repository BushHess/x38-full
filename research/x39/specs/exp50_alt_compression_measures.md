# Exp 50: Alternative Compression Measures — Mechanism Robustness

## Status: DONE

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

**Verdict: MECHANISM FRAGILE** — 0/4 alternative measures are selective.

Baseline: Sharpe 1.2965, WR 41.2%, 221 trades.
Thresholds calibrated to block ~30% of entries at each measure's P70.

| Measure | Sharpe | d_Sharpe | Blocked WR | Selective? | Corr w/ vol_ratio_5_20 |
|---------|--------|----------|------------|------------|------------------------|
| vol_ratio_5_20 | 1.4470 | +0.1505 | 32.8% | YES | — |
| atr_ratio_5_20 | 1.2709 | -0.0256 | 47.7% | NO | 0.564 |
| range_ratio_5_20 | 1.2709 | -0.0256 | 47.7% | NO | 0.564 |
| bb_pctl | 1.0936 | -0.2029 | 44.7% | NO | -0.201 |
| vol_ratio_5_50 | 1.3763 | +0.0798 | 42.9% | NO | 0.749 |

Key findings:
1. **Only vol_ratio_5_20 is selective** (blocked WR 32.8% < 41.2% baseline).
   All 4 alternatives block winners at equal or higher rate than baseline.
2. **atr_ratio and range_ratio are identical** (r=1.000) — crypto H4 has no
   gaps, so true_range ≈ high-low. Functionally one measure, not two.
3. **bb_pctl anti-correlated** (r=-0.201) — measures absolute vol level,
   not short/long ratio. Different concept entirely.
4. **vol_ratio_5_50 closest** (r=0.749, d_Sharpe +0.08) but fails selectivity
   (blocked WR 42.9% ≈ baseline). Wider window dilutes the signal.
5. The compression mechanism is **feature-specific**: close-to-close std at
   exactly 5/20 windows captures something that range-based and ATR-based
   alternatives do not. This is a caution flag for vol_ratio_5_20's WFO result.
