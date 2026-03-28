# Exp 49: Compression + Maturity Decay Combo Walk-Forward Validation

## Status: DONE

## Hypothesis
Exp44 showed compression + maturity decay is ADDITIVE (ratio 0.79):
combo_B (thr=0.7, min=1.5/60/180) → Sharpe 1.543, d_Sh +0.233.

However:
- exp42 (compression alone) PASSES WFO 4/4
- exp40 (maturity decay alone) FAILS WFO 2/4 (bear-only benefit)

The open question: does compression's selectivity "clean" the trade
population enough that maturity decay becomes WFO-stable on the
filtered set?

Reasoning: maturity decay fails WFO because it cuts winning trades in
bull markets (the fat-tail constraint). But compression removes the
WORST entries — specifically entries during expanded volatility that are
more likely to whipsaw. On this filtered population, the remaining
trades may have more uniform duration characteristics, making maturity
decay's trail tightening less harmful in bull regimes.

If this combo passes WFO → the best available improvement (+0.233 Sharpe
full-sample, +0.26 WFO compression-only). Even if the combo WFO delta
is less than compression-only, it's worth testing because the full-sample
combo dominates compression-only on Sharpe AND MDD.

If this combo fails WFO → maturity decay is fundamentally regime-dependent
regardless of entry population. Deploy compression alone.

## Baseline
E5-ema21D1 (simplified replay): ~1.30 Sharpe, ~197 trades.

## WFO Design
Anchored walk-forward, 4 windows (same as exp40/42):
```
Window 1: Train [2019-01 → 2021-06]  Test [2021-07 → 2023-06]
Window 2: Train [2019-01 → 2022-06]  Test [2022-07 → 2024-06]
Window 3: Train [2019-01 → 2023-06]  Test [2023-07 → 2025-06]
Window 4: Train [2019-01 → 2024-06]  Test [2024-07 → 2026-02]
```

## Configurations to test (NO training sweep for compression — use fixed)

Compression threshold is FIXED at 0.7 (WFO-validated in exp42).
Only decay parameters are swept in training:

Train sweep (decay params only):
- trail_min: [1.5, 2.0, 2.5]
- decay_start: [30, 60] (H4 bars)
- decay_end: [120, 180, 240] (H4 bars)
- constraint: decay_start < decay_end
- (18 configs, same grid as exp40)

Fixed configs:
- Fixed A: thr=0.7 + min=1.5/60/180 (exp44 combo_B optimum)
- Fixed B: thr=0.7 + min=2.0/60/180 (less aggressive decay)
- Fixed C: thr=0.7, no decay (exp42 result, for comparison)

## Procedure per window
1. **Train**: fix thr=0.7, sweep 18 decay configs → select best Sharpe
2. **Test**: run selected + fixed A + fixed B + fixed C (comp-only) + baseline
3. Record: d_Sharpe vs baseline, d_Sharpe vs comp-only (Fixed C)

## What to measure
Per window:
- Combo d_Sharpe vs baseline (target: > compression-only d_Sharpe)
- Comp-only d_Sharpe vs baseline (reproduction of exp42 for consistency)
- Marginal decay value = combo_d_Sharpe - comp_only_d_Sharpe
  (positive = decay adds value on top of compression)

Aggregate:
- WFO win rate ≥ 3/4 AND mean d_Sharpe > 0 (combo vs baseline)
- **CRITICAL**: is marginal decay value > 0 in ≥ 3/4 windows?
  If yes → decay adds value conditionally (even though it fails standalone)
  If no → deploy compression alone

## Implementation notes
- Combine exp42's compression logic with exp38/40's decay logic
- Compression threshold is NOT swept (WFO-validated at 0.7) — this avoids
  adding DOF to the combo that hasn't been validated
- Only decay parameters are swept in training
- Force-close at window end (consistent with exp40/42)
- Warmup: 365 days, Cost: 50 bps RT

## Output
- Script: x39/experiments/exp49_compression_decay_wfo.py
- Results: x39/results/exp49_results.csv

## Result

**VERDICT: COMPRESSION_ONLY** — Decay adds no marginal value on top of compression.

### Compression-only (thr=0.7, Fixed C) — exp42 reproduction
- WFO: **4/4 (100%)**, mean d_Sharpe **+0.2473**
- d_Sharpe per window: [+0.33, +0.33, +0.15, +0.18]
- Mean d_MDD: **-5.52 pp** (improvement)

### Combo results (vs baseline)
| Config | WFO | Mean d_Sh | d_Sh/window | Mean d_MDD |
|--------|-----|-----------|-------------|------------|
| Selected | 3/4 (75%) | +0.133 | [+0.56, +0.09, -0.17, +0.06] | -5.88 pp |
| Fixed A (1.5/60/180) | 3/4 (75%) | +0.134 | [+0.56, +0.09, -0.17, +0.06] | -4.96 pp |
| Fixed B (2.0/60/180) | 4/4 (100%) | +0.237 | [+0.51, +0.31, +0.07, +0.06] | -5.25 pp |

### CRITICAL: Marginal decay value (combo - comp-only)
| Config | Marg wins | Mean marg | Per window |
|--------|-----------|-----------|------------|
| Selected | **1/4 FAIL** | -0.115 | [+0.23, -0.24, -0.32, -0.12] |
| Fixed A | **1/4 FAIL** | -0.113 | [+0.23, -0.24, -0.32, -0.12] |
| Fixed B | **1/4 FAIL** | -0.011 | [+0.18, -0.02, -0.08, -0.12] |

### Key findings
1. **Decay only helps in W1 (bear)**, hurts in all other windows → bear-only benefit persists
2. Compression CANNOT fix decay's regime-dependence — bear mean marginal -0.006, bull mean marginal **-0.220**
3. Parameter stability STABLE (2 unique: min=1.5/60/180 for W1-3, min=2.0/60/180 for W4)
4. All combos pass WFO vs baseline, but ALL are **worse** than compression-only
5. Fixed B (less aggressive decay) is closest to compression-only but still net negative marginal

### Conclusion
Deploy **compression alone** (thr=0.7). Maturity decay is fundamentally regime-dependent
regardless of entry population quality. The hypothesis that compression "cleans" the trade
population enough for decay to work is **rejected**.
