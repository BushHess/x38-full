# Exp 44: Vol Compression Gate + Maturity Decay Combination

## Status: DONE

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

### Summary table

| Config | Thr | Min | Start | End | Sharpe | CAGR% | MDD% | Trades | d_Sharpe | d_MDD |
|--------|-----|-----|-------|-----|--------|-------|------|--------|----------|-------|
| baseline | - | - | - | - | 1.310 | 52.70 | 41.01 | 197 | - | - |
| exp34_only | 0.6 | - | - | - | 1.455 | 59.52 | 38.42 | 177 | +0.145 | -2.59 |
| exp38_only | - | 1.5 | 60 | 180 | 1.460 | 58.11 | 31.19 | 263 | +0.150 | -9.82 |
| **combo_B** | **0.7** | **1.5** | **60** | **180** | **1.543** | **60.81** | **31.48** | **240** | **+0.233** | **-9.53** |
| combo_A | 0.6 | 1.5 | 60 | 180 | 1.537 | 59.84 | 31.48 | 233 | +0.227 | -9.53 |
| combo_C | 0.6 | 1.5 | 60 | 240 | 1.532 | 60.05 | 31.48 | 225 | +0.223 | -9.53 |
| combo_D | 0.6 | 2.0 | 60 | 180 | 1.508 | 59.78 | 33.65 | 210 | +0.198 | -7.36 |
| combo_E | 0.8 | 1.5 | 60 | 180 | 1.472 | 57.72 | 31.48 | 247 | +0.163 | -9.53 |
| combo_F | 0.5 | 1.5 | 60 | 180 | 1.491 | 56.24 | 38.52 | 224 | +0.181 | -2.49 |

### Key question answer
**NO** — no combo achieves BOTH Sharpe >= exp34 AND MDD <= exp38 strictly.
All combos achieve Sharpe >= exp34 (SHARPE_ONLY), but MDD is 31.48% vs exp38's
31.19% — a 0.29pp gap. Compression's MDD penalty is *nearly* neutralized but
not fully eliminated.

### Additivity analysis
- **Best combo: combo_B** (thr=0.7, min=1.5, start=60, end=180)
  - Sharpe 1.543, CAGR 60.81%, MDD 31.48%, 240 trades
  - d_Sharpe +0.233, additivity ratio 0.790 → **ADDITIVE**
- Sum of individual deltas: +0.295 (exp34 +0.145 + exp38 +0.150)
- combo_B achieves 79% of theoretical sum → mechanisms are largely independent
- combo_A (thr=0.6) ratio 0.770, combo_C (longer decay) ratio 0.756 — also ADDITIVE
- combo_D (min=2.0) and combo_E/F — PARTIALLY_ADDITIVE (0.55-0.67)

### MDD analysis
- exp38-only dominates MDD: 31.19% (best single, -9.82pp)
- Most combos converge to ~31.48% MDD — decay drives MDD, compression barely moves it
- combo_F (thr=0.5, most aggressive) MDD 38.52% — too aggressive entry filter
  causes re-entry at worse points, losing the MDD benefit

### Compression gate statistics
- Block rate at thr=0.6: 40.3% of base entry signals blocked
- combo_B (thr=0.7): 237 blocked, less aggressive → better CAGR/Sharpe balance

### Conclusion
**ADDITIVE** — combination is justified. Entry (compression) and exit (maturity
decay) independently contribute. combo_B (thr=0.7) is best overall config.
Sharpe improvement +0.233 over baseline beats both singles. MDD 31.48% is
0.29pp worse than exp38-only (31.19%) — near-miss on strict dominance.
The 0.29pp MDD gap is negligible in practice.
