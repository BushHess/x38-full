# Exp 20: Rangepos-Adaptive Trail

## Status: DONE

## Hypothesis
E5 uses fixed trail_mult = 3.0. Exp11 tested D1 anti-vol for dynamic trail
adjustment → FAIL (best d_Sharpe = +0.003, effectively zero).

However, exp11 used d1_rangevol84_rank365 as the modulator — a D1-resolution
feature with only 1/5 significant residual horizons for forward returns.
rangepos_84 is a BETTER candidate: it operates at H4 resolution, has 3/5
significant residual horizons, and exp12 proved its exit value (+0.046 Sharpe).

The idea: instead of binary exit (exp12: rangepos < 0.25 → exit), use
rangepos_84 as a CONTINUOUS modulator of trail width.

- rangepos_84 high (near range top) → price healthy → WIDEN trail → let winners run
- rangepos_84 low (near range bottom) → price stressed → TIGHTEN trail → protect gains

This is mechanistically different from exp12:
- exp12 EXITS when rangepos drops below threshold (binary, immediate)
- exp20 TIGHTENS the trail (continuous, gradual protection that may or may not trigger)

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Feature
```
rolling_high_84[i] = max(high[i-83:i+1])
rolling_low_84[i]  = min(low[i-83:i+1])
rangepos_84[i] = (close[i] - rolling_low_84[i]) / (rolling_high_84[i] - rolling_low_84[i])
# Range: [0, 1]. 0 = at 84-bar low, 1 = at 84-bar high.
```

## Modification to E5-ema21D1
Entry logic UNCHANGED.
Exit — dynamic trail multiplier modulated by rangepos_84:
```python
# Linear interpolation between tight_mult and wide_mult
# based on rangepos_84 position:
trail_mult = tight_mult + rangepos_84[i] * (wide_mult - tight_mult)

# When rangepos_84 = 0 (range bottom): trail_mult = tight_mult (tighter)
# When rangepos_84 = 1 (range top):    trail_mult = wide_mult  (wider)

trail_stop = peak_price - trail_mult * ratr[i]
exit_signal = close < trail_stop OR ema_fast < ema_slow
```

## Parameter sweep
- tight_mult in [1.5, 2.0, 2.5]
- wide_mult in [3.0, 3.5, 4.0]
- Constraint: tight_mult < wide_mult (9 valid combos, all satisfy)
- Also include: baseline (fixed 3.0) for reference

Total: 9 configs + 1 baseline = 10 runs.

| Config | tight (rp=0) | wide (rp=1) | At rp=0.5 |
|--------|-------------|-------------|-----------|
| A      | 1.5         | 3.0         | 2.25      |
| B      | 1.5         | 3.5         | 2.50      |
| C      | 1.5         | 4.0         | 2.75      |
| D      | 2.0         | 3.0         | 2.50      |
| E      | 2.0         | 3.5         | 2.75      |
| F      | 2.0         | 4.0         | 3.00      |
| G      | 2.5         | 3.0         | 2.75      |
| H      | 2.5         | 3.5         | 3.00      |
| I      | 2.5         | 4.0         | 3.25      |

Note: config F at rp=0.5 equals baseline (3.0). Config H at rp=0.5 also equals
baseline. This provides built-in sanity checks.

## What to measure
For each config AND baseline:
- Sharpe, CAGR%, MDD%, trade count, win rate, avg holding period, exposure%
- Delta vs baseline for Sharpe, CAGR, MDD
- Distribution of effective trail_mult values during trades (median, p10, p90)
- How many trades exit EARLIER vs LATER than baseline? (pair each trade with
  its baseline counterpart by entry bar)

## Implementation notes
- Use x39/explore.py's compute_features() to get rangepos_84 array
- Trail multiplier changes bar-by-bar during a trade (not just at entry)
- Peak price tracking is same as baseline — only the trail WIDTH changes
- Handle NaN in rangepos_84 during warmup: use fixed 3.0 as fallback
- Data: bars_btcusdt_2016_now_h1_4h_1d.csv
- Cost: 50 bps RT (harsh)
- Warmup: skip first 365 days (same as other experiments)

## Output
- Script: x39/experiments/exp20_rangepos_adaptive_trail.py
- Results: x39/results/exp20_results.csv

## Result

**FAIL**: All 9 adaptive trail configs degrade both Sharpe and MDD vs baseline.

### Summary Table (deltas vs baseline)

| Config | tight | wide | Sharpe | d_Sharpe | CAGR% | d_MDD pp | Trades | trail_median |
|--------|-------|------|--------|----------|-------|----------|--------|-------------|
| base   | 3.0   | 3.0  | 1.2965 | —        | 57.77 | —        | 221    | 3.000       |
| A      | 1.5   | 3.0  | 1.1566 | -0.1399  | 48.01 | +5.46    | 274    | 2.730       |
| B      | 1.5   | 3.5  | 1.2078 | -0.0887  | 51.64 | +3.08    | 248    | 3.135       |
| C      | 1.5   | 4.0  | 1.1239 | -0.1726  | 46.67 | +7.38    | 227    | 3.538       |
| D      | 2.0   | 3.0  | 1.1675 | -0.1290  | 49.03 | +5.15    | 252    | 2.817       |
| E      | 2.0   | 3.5  | 1.2039 | -0.0926  | 51.81 | +5.44    | 228    | 3.223       |
| F      | 2.0   | 4.0  | 1.1305 | -0.1660  | 47.43 | +6.67    | 215    | 3.625       |
| G      | 2.5   | 3.0  | 1.1810 | -0.1155  | 50.13 | +4.92    | 237    | 2.908       |
| H      | 2.5   | 3.5  | 1.1508 | -0.1457  | 48.63 | +0.99    | 219    | 3.313       |
| I      | 2.5   | 4.0  | 1.1890 | -0.1075  | 51.12 | +2.28    | 200    | 3.714       |

Best d_Sharpe: none positive. Closest: I (-0.1075). Best d_MDD: H (+0.99 pp, barely worse).

### Trade exit timing (vs baseline)

Tighter configs (A, D, G) exit EARLIER (up to 121/200 matched trades). Wider configs
(F, H, I) exit LATER (up to 74/184). This confirms the mechanism works as designed —
it just doesn't help.

Key pattern: configs with median trail < 3.0 generate MORE trades (churn) and degrade
Sharpe. Configs with median trail > 3.0 hold longer but suffer worse drawdowns.
The fixed trail=3.0 sits at a sweet spot that continuous modulation cannot improve.

### Trail_mult distribution

rangepos_84 during trades is skewed high (median ~0.82 for close-to-range-top). This
means adaptive trail spends most time near wide_mult, explaining why F/H medians (3.625,
3.313) exceed baseline 3.0 despite midpoint=3.0. The asymmetry confirms sanity but
reveals the modulator is not centered — most in-trade bars are near range highs.

### Interpretation

This result is consistent with exp11 (D1 anti-vol trail → FAIL, d_Sharpe +0.003) and
the trail sweep finding from X16: trail width is NOT the bottleneck. The fixed trail=3.0
is already near-optimal, and continuous adaptation adds noise without improving the
return/risk tradeoff. rangepos_84 has exit value (exp12: +0.046 Sharpe as binary exit)
but not trail-width-modulation value.
