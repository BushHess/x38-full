# Exp 26: AND-Gate Fine Grid

## Status: DONE

## Hypothesis
Exp22's heatmap shows a sharp drop between rp=0.20 and rp=0.25:
```
d_Sharpe at tq=-0.10:  rp=0.20: +0.0569  |  rp=0.25: +0.0311  (-0.026 drop)
```
This 0.026 drop in a 0.05 step is concerning — it suggests rp=0.20 might be
a sharp peak rather than part of a plateau. The heatmap also doesn't include
rp < 0.20. We don't know if performance continues to improve below 0.20
(which would suggest a plateau ending at 0.20) or if 0.20 is an isolated peak.

Similarly, the tq dimension appears stable from -0.10 to 0.30, but the grid
is coarse (0.20 steps). Finer resolution reveals whether the stability is real.

This experiment maps the AND gate's parameter landscape at high resolution
to determine: **is (rp=0.20, tq=-0.10) a robust operating point or a
lucky intersection of two fragile dimensions?**

## Baseline
E5-ema21D1 (simplified replay): ~1.2965 Sharpe, ~51.32% MDD, 221 trades.

## Features
```
rangepos_84[i] = (close[i] - rolling_low_84[i]) / (rolling_high_84[i] - rolling_low_84[i])
trendq_84[i]   = ret_84[i] / realized_vol_84[i]
```
Same as exp22. This experiment only refines the threshold grid.

## Modification to E5-ema21D1
Entry logic UNCHANGED.
Exit — AND gate (same as exp22):
```python
# close < trail_stop OR ema_fast < ema_slow
# OR (rangepos_84 < rp_threshold AND trendq_84 < tq_threshold)
```

## Parameter sweep
Fine 2D grid centered around (rp=0.20, tq=-0.10):

- rp_threshold in [0.10, 0.13, 0.16, 0.19, 0.22, 0.25, 0.28]
  (step 0.03, extends BELOW 0.20 to explore left side)
- tq_threshold in [-0.25, -0.18, -0.10, -0.03, 0.05, 0.12, 0.20]
  (step ~0.07, centered on -0.10)

Total: 7 × 7 = 49 configs + 1 baseline = 50 runs.

## What to measure
For each config AND baseline:
- Sharpe, CAGR%, MDD%, trade count, AND gate exit count
- Delta vs baseline for Sharpe, MDD

Key analysis:
1. **rp dimension cross-section**: at tq=-0.10, plot d_Sharpe vs rp_threshold.
   - If rp=0.10-0.19 forms a plateau → robust. rp=0.20 is right edge.
   - If rp=0.19-0.20 is a sharp peak → fragile.
   - If rp < 0.16 improves further → exp22 missed the real optimum.

2. **tq dimension cross-section**: at rp=0.20, plot d_Sharpe vs tq_threshold.
   - Confirm/deny the plateau observed in exp22's coarse grid.
   - Is there a finer structure hidden in the 0.20 steps?

3. **Contour map**: 2D contour of d_Sharpe across the (rp, tq) grid.
   - Identify shape: round peak (fragile), ridge (partially robust),
     plateau (robust), or diagonal (correlated fragility).

4. **Exit count vs performance**: plot d_Sharpe vs AND gate exit count
   across all 49 configs. If there's a clear sweet spot (10-20 exits),
   the mechanism has a structural explanation.

5. **Gradient magnitude**: at the optimum, compute |∂Sharpe/∂rp| and
   |∂Sharpe/∂tq|. Large gradient = fragile. Threshold for concern:
   |gradient| > 0.5 Sharpe per unit threshold.

## Implementation notes
- Use exp22 code as base, only change the parameter grid
- Data: bars_btcusdt_2016_now_h1_4h_1d.csv
- Cost: 50 bps RT (harsh)
- Warmup: 365 days
- Consider printing results as a formatted 7×7 grid for visual inspection

## Output
- Script: x39/experiments/exp26_and_gate_fine_grid.py
- Results: x39/results/exp26_results.csv

## Result

**Baseline**: Sharpe 1.2965, CAGR 57.77%, MDD 51.32%, 221 trades.

### Heatmap (d_Sharpe, rows=rp, cols=tq)
```
tq→       -0.25   -0.18   -0.10   -0.03    0.05    0.12    0.20
rp=0.10  -0.008  +0.009  +0.024  +0.024  +0.004  +0.004  +0.004
rp=0.13  -0.007  +0.027  +0.025  +0.025  +0.005  +0.005  +0.005
rp=0.16  -0.004  +0.030  +0.023  +0.039  +0.019  +0.013  +0.013
rp=0.19  +0.006  +0.050  +0.043  +0.073  +0.048  +0.048  +0.048
rp=0.22  -0.009  +0.063  +0.052  +0.082  +0.053  +0.061  +0.054
rp=0.25  -0.016  +0.049  +0.031  +0.062  +0.028  +0.043  +0.039
rp=0.28  -0.036  +0.015  -0.008  +0.019  -0.023  -0.024  -0.028
```

### Key findings

1. **Optimum shifted**: Best point is **(rp=0.22, tq=-0.03)**, not exp22's (rp=0.20, tq=-0.10).
   d_Sharpe=+0.0817, d_MDD=-6.06 pp, 16 AND gate exits.

2. **rp cross-section at tq=-0.10** — RIDGE shape (partially robust):
   - rp=0.10→0.22: all positive d_Sharpe (+0.024 to +0.052)
   - rp=0.22 is peak (+0.052), sharp drop at rp=0.28 (-0.008)
   - 3/7 points within 50% of peak

3. **tq cross-section at rp=0.19** — HIGH variation (range 0.067):
   - tq=-0.25 weak (+0.006), tq=-0.18 to tq=0.20 forms plateau (+0.043 to +0.073)
   - tq=-0.03 best (+0.073), not tq=-0.10 (+0.043)
   - Sharp drop below tq=-0.18

4. **Contour shape**: 39/49 configs improve BOTH Sharpe and MDD vs baseline.
   Only tq=-0.25 column and rp=0.28 row are danger zones.

5. **Gradient at optimum**: |drp|=0.188, |dtq|=0.010 — both BELOW 0.5 threshold → ROBUST.
   At exp22 ref (rp=0.19, tq=-0.10): |drp|=0.472 (borderline), |dtq|=0.153.

6. **Exit count sweet spot**: Best configs have 10-16 AND exits. >25 exits degrades performance.

### Verdict

**ROBUST** — the AND gate operating region is a broad ridge, not a fragile peak.
- rp has a functional range of ~0.13 to 0.25 (all positive d_Sharpe at tq≥-0.18)
- tq has a functional range of ~-0.18 to 0.20 (plateau above -0.18)
- (rp=0.20, tq=-0.10) from exp22 sits safely inside the viable region, NOT on a cliff edge
- True optimum at (rp=0.22, tq=-0.03) with mild gradients

The sharp drop exp22 observed at rp=0.25 is confirmed but is the right edge of a broad ridge,
not a cliff next to a narrow peak. Performance degrades gracefully toward the edges.
