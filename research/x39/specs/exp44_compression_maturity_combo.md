# Exp 44: Vol Compression Gate + Maturity Decay Combination

## Status: PENDING

## Hypothesis
Exp34 (vol compression) shows the LARGEST Sharpe improvement in x39
(+0.190 at threshold=0.6) with genuine selectivity (blocked WR < baseline WR).
Exp38 (maturity decay) shows the most robust improvement (+0.150 Sharpe,
18/18 MDD improve).

Exp34's weakness is MDD: +2.3pp at threshold=0.6. Exp38's strength IS MDD
(-9.82pp). Combining compression entry + maturity exit may capture exp34's
Sharpe gain while exp38's maturity decay fixes the MDD weakness.

This tests: can compression's MDD penalty be neutralized by maturity decay?

Mathematical motivation: entry quality (compression) and exit timing
(maturity) are structurally independent. Compression selects BETTER entries
(lower loss rate); maturity protects EXISTING profits (tighter late-trail).
If independent, the combined effect = Sharpe of compression + MDD
improvement of maturity.

## Baseline
E5-ema21D1 (simplified replay): ~1.30 Sharpe, ~197 trades.

## Components
```
# Exp34 best: entry gate
compression_threshold = 0.6 (or 0.7)
entry: base_conditions AND vol_ratio_5_20 < threshold

# Exp38 best: exit modification
trail_min = 1.5, decay_start = 60, decay_end = 180
effective_trail decays linearly from 3.0 → 1.5 over bars 60-180 of trend age
```

## Modification to E5-ema21D1
```python
# Entry (exp34):
#   ema_fast > ema_slow AND vdo > 0 AND d1_regime_ok
#   AND vol_ratio_5_20 < compression_threshold

# Exit (exp38):
#   effective_trail = decay(trend_age, 3.0, trail_min, decay_start, decay_end)
#   trail_stop = peak - effective_trail * robust_atr
#   exit if close < trail_stop OR ema_fast < ema_slow
```

## Parameter sweep
```
# Fixed at best single-experiment configs
combo_A: thr=0.6, min=1.5, start=60, end=180
combo_B: thr=0.7, min=1.5, start=60, end=180   # less aggressive entry

# Vary exit with best entry
combo_C: thr=0.6, min=1.5, start=60, end=240
combo_D: thr=0.6, min=2.0, start=60, end=180

# Vary entry with best exit
combo_E: thr=0.8, min=1.5, start=60, end=180
combo_F: thr=0.5, min=1.5, start=60, end=180   # most aggressive entry
```
Plus: baseline, exp34-only (thr=0.6), exp38-only (min=1.5/60/180)
(9 total: 6 combos + 3 references)

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, exposure%.
Delta vs baseline, vs exp34-only, vs exp38-only.

Key question: does combo_A achieve BOTH Sharpe ≥ exp34 AND MDD ≤ exp38?
If yes → the combination is strictly better than either component alone.

Also: additivity ratio (same as exp43), trade count impact.

## Implementation notes
- vol_ratio_5_20 is already in compute_features() — use directly
- Combine with exp38's decay logic
- Warmup: 365 days (consistent with exp38)
- Cost: 50 bps RT

## Output
- Script: x39/experiments/exp44_compression_maturity_combo.py
- Results: x39/results/exp44_results.csv

## Result
_(to be filled by experiment session)_
