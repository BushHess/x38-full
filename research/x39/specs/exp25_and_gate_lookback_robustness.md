# Exp 25: AND-Gate Lookback Robustness

## Status: DONE

## Hypothesis
Exp23 showed rangepos_84 as standalone exit is FRAGILE: L=84 is a sharp peak
(Sharpe range 0.1525 across lookbacks), not a plateau. This raises a critical
question: **does exp22's AND gate inherit rangepos's fragility, or does
trendq confirmation stabilize it?**

The AND gate (rp < 0.20, tq < -0.10) fires only 12 times (vs rangepos-only's
35 exits at rp=0.25). If trendq acts as a quality filter on rangepos triggers,
the AND gate should be LESS sensitive to lookback choice — trendq compensates
for false alarms caused by lookback mismatch.

Alternatively, if AND gate Sharpe also collapses at L≠84, the entire
rangepos-based exit line (exp12, exp22) is overfit to the specific L=84
window (14 days ≈ half BTC swing cycle) and not a robust mechanism.

This is the MOST IMPORTANT experiment in the new wave: it determines
whether the AND gate finding (exp22) is real or an artifact.

## Baseline
E5-ema21D1 (simplified replay): ~1.2965 Sharpe, ~51.32% MDD, 221 trades.

## Features
```
# Rangepos with variable lookback L:
rangepos_L[i] = (close[i] - rolling_low_L[i]) / (rolling_high_L[i] - rolling_low_L[i])

# Trendq (FIXED at 84 bars — not varied):
trendq_84[i] = ret_84[i] / realized_vol_84[i]
```

## Modification to E5-ema21D1
Entry logic UNCHANGED.
Exit — AND gate with variable rangepos lookback:
```python
# close < trail_stop OR ema_fast < ema_slow
# OR (rangepos_L < rp_threshold AND trendq_84 < tq_threshold)
```

## Parameter sweep
Fix tq_threshold = -0.10 (exp22 optimum, stable across tq dimension).
Vary rangepos lookback AND threshold together:

- L in [42, 63, 84, 105, 126, 168]
- rp_threshold in [0.15, 0.20, 0.25, 0.30]
- (24 configs)

Also include for reference:
- rangepos-only at each L × rp_threshold (exp23 reproduction, 24 configs)
- baseline (no supplementary exit)

Grand total: 49 runs.

Note: L=105 (17.5 days) is NEW — fills the gap between 84 and 126 to test
whether the peak is truly sharp or has a shoulder we missed in exp23.

## What to measure
For each config:
- Sharpe, CAGR%, MDD%, trade count, AND gate exit count
- Delta vs baseline for Sharpe, MDD

Key analysis:
1. **AND gate lookback sensitivity**: at fixed rp=0.20, tq=-0.10, plot
   AND gate d_Sharpe vs L. Compare with rangepos-only d_Sharpe vs L (exp23).
   If AND gate curve is FLATTER → trendq stabilizes. If equally sharp → fragile.

2. **Sharpe range metric**: compute max(Sharpe) - min(Sharpe) across L for:
   - AND gate at rp=0.20
   - rangepos-only at rp=0.25
   Threshold: range < 0.05 = robust plateau, range > 0.10 = fragile.

3. **Optimal L per mechanism**: does AND gate prefer different L than
   rangepos-only? If AND shifts the optimal L, this reveals what trendq
   compensates for.

4. **Exit count vs L**: how does AND gate selectivity change with L?
   Shorter L → more rangepos triggers → AND should filter more.

## Implementation notes
- Use exp22 code as base, parameterize rangepos lookback
- trendq_84 stays FIXED at 84 bars (this experiment isolates rangepos L effect)
- Compute rangepos for each L separately using pandas rolling
- Data: bars_btcusdt_2016_now_h1_4h_1d.csv
- Cost: 50 bps RT (harsh)
- Warmup: 365 days

## Output
- Script: x39/experiments/exp25_and_gate_lookback_robustness.py
- Results: x39/results/exp25_results.csv

## Result

**VERDICT: MODERATE** — trendq provides PARTIAL stabilization (55% range reduction),
but AND gate is not a fully robust plateau.

### Key findings

1. **Sharpe range (AND gate rp=0.20)**: 0.0687 — MODERATE (between 0.05 and 0.10)
   vs RP-only (rp=0.25): 0.1525 — FRAGILE. Ratio 0.45x → **55% range reduction**.

2. **AND gate lookback sensitivity** (rp=0.20, tq=-0.10):
   ```
     L     AND Sharpe  AND d_Sh  AND exits   RP Sharpe  RP d_Sh  RP exits
    42      1.3439     +0.0474       31       1.1902   -0.1063     156
    63      1.3264     +0.0299       23       1.2716   -0.0249      90
    84      1.3534     +0.0569       12       1.3427   +0.0462      35
   105      1.2989     +0.0024        7       1.3294   +0.0329      18
   126      1.2954     -0.0011        3       1.2771   -0.0194      13
   168      1.2847     -0.0118        2       1.2766   -0.0199       8
   ```

3. **AND gate beats baseline at 4/6 lookbacks** (L=42-105), fails at L=126,168
   (too few AND exits at long lookbacks: 1-3 exits → near-baseline).
   RP-only beats baseline at only 3/6 lookbacks at rp=0.25.

4. **trendq filters most aggressively at short L**: AND/RP ratio = 0.29 at L=42
   (trendq blocks 71% of rangepos triggers), 0.71 at L=84. At L≥126, both are
   identical (same 3 or fewer exits).

5. **Optimal L is the same for both**: L=84 for both AND and RP-only at rp=0.20.
   AND does NOT shift the optimal lookback — trendq confirms the L=84 window,
   not compensates for it.

6. **Best AND config**: L=84, rp=0.20 → Sharpe 1.3534 (+0.0569), MDD 44.24% (-7.08 pp),
   12 AND exits, 83.3% selectivity. Reproduces exp22 exactly.

7. **rp=0.30 consistently degrades AND gate**: negative d_sharpe at 4/6 lookbacks.
   rp=0.15 is too tight (few exits). Sweet spot: rp=0.20 at L=63-84.

8. **AND gate Sharpe range by threshold**:
   - rp=0.15: 0.0670 (MODERATE)
   - rp=0.20: 0.0687 (MODERATE)
   - rp=0.25: 0.0513 (MODERATE)
   - rp=0.30: 0.0432 (ROBUST)
   Tighter rp → fewer exits → approaches baseline (trivially robust).

### Interpretation

The AND gate provides REAL but PARTIAL stabilization. At short lookbacks (L=42),
where RP-only fails catastrophically (-0.1063 Sharpe at rp=0.25), the AND gate
still improves (+0.0474 at rp=0.20). Trendq blocks 71% of false rangepos triggers
at L=42 — this is genuine quality filtering.

However, the AND gate does NOT create a lookback-invariant mechanism. L=84 remains
clearly optimal (peak, not plateau), and L≥126 produces near-baseline results due
to too few rangepos triggers for trendq to filter.

**The AND gate is not overfit** (it works across L=42-105), but it is
**L=84-concentrated** — the best config is still the exp22 original. The finding
is confirmed as real, not an artifact, but the lookback choice still matters.
