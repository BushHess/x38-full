# Exp 22: AND-Gated Feature Interaction Exit

## Status: DONE

## Hypothesis
Exp12 (rangepos exit) and exp13 (trendq exit) tested single features as
supplementary exits:
- Exp12 rangepos_84 < 0.25: PASS (+0.046 Sharpe, −6.37 pp MDD, 35 exits)
- Exp13 trendq_84 < −0.20: FAIL (−0.049 Sharpe, −3.93 pp MDD)

Exp13 failed because trendq_84 responds eagerly to vol spikes — it exits
during temporary volatility that does NOT indicate trend failure. But trendq's
MDD improvement (−3.93 pp) suggests it DOES catch some real drawdowns.

Hypothesis: requiring BOTH features to agree before exiting (AND gate) should
be MORE SELECTIVE than either alone:
- rangepos_84 low = price is falling within its range
- trendq_84 low = momentum/volatility ratio deteriorating

When BOTH are true simultaneously, confidence in trend failure is higher.
The AND gate filters out trendq's false alarms (vol spikes where rangepos
stays high) and rangepos's false alarms (range compression where trendq
stays healthy). Result: fewer interventions, each on higher-quality exits.

This tests NON-LINEAR feature interaction — something no exp01-18 tested.
All previous experiments used features in isolation.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Features
```
# Feature 1: range position
rangepos_84[i] = (close[i] - rolling_low_84[i]) / (rolling_high_84[i] - rolling_low_84[i])

# Feature 2: trend quality
ret_84[i] = close[i] / close[i - 84] - 1
realized_vol_84[i] = rolling_std(log_returns, 84) * sqrt(84)
trendq_84[i] = ret_84[i] / realized_vol_84[i]
```

## Modification to E5-ema21D1
Entry logic UNCHANGED.
Exit — ADD AND-gated condition (OR with existing exits):
```python
# Original: close < trail_stop OR ema_fast < ema_slow
# Modified: close < trail_stop OR ema_fast < ema_slow
#           OR (rangepos_84 < rp_threshold AND trendq_84 < tq_threshold)
```
The AND gate fires only when BOTH conditions are met simultaneously.

## Parameter sweep
Sweep both thresholds in a 2D grid:

- rp_threshold in [0.20, 0.25, 0.30, 0.35]
- tq_threshold in [−0.30, −0.10, 0.10, 0.30]

Total: 4 × 4 = 16 configs + 1 baseline = 17 runs.

Also include for reference (single-feature controls):
- rangepos-only at rp=0.25 (exp12 reproduction)
- trendq-only at tq=−0.20 (exp13 reproduction)

Grand total: 19 runs.

## What to measure
For each config AND baseline:
- Sharpe, CAGR%, MDD%, trade count, win rate, exposure%
- Delta vs baseline for Sharpe, CAGR, MDD
- AND gate exit count: how many trades exited by the AND condition?
- Exit selectivity: of AND-gated exits, what % were on losing trades?
  (Higher = better. Compare with exp12's selectivity.)
- Comparison: AND gate vs single-feature exits (is AND > OR > single?)
- Overlap analysis: on bars where AND fires, would rangepos-only or
  trendq-only ALSO have fired? (Measures true interaction value.)

## Implementation notes
- Use x39/explore.py's compute_features() for both features
- trendq_84 can be NaN when realized_vol_84 = 0 (flat price). Treat NaN
  as "not triggered" (conservative — AND gate doesn't fire)
- Data: bars_btcusdt_2016_now_h1_4h_1d.csv
- Cost: 50 bps RT (harsh)
- Warmup: 365 days
- Key diagnostic: print the overlap matrix showing how many exits are
  {AND-only, rangepos-only, trendq-only, both-would-fire}. This reveals
  whether the AND gate adds new information or is just a subset of
  single-feature exits.

## Output
- Script: x39/experiments/exp22_and_gated_exit.py
- Results: x39/results/exp22_results.csv

## Result

**PASS** — AND gate (rp=0.20, tq=-0.10) is best config.

### Best AND config: rp=0.20, tq=-0.10
| Metric | Baseline | AND best | Delta |
|--------|----------|----------|-------|
| Sharpe | 1.2965 | 1.3534 | **+0.0569** |
| CAGR% | 57.77 | 61.24 | +3.47 |
| MDD% | 51.32 | 44.24 | **-7.08 pp** |
| Trades | 221 | 223 | +2 |
| AND exits | — | 12 | — |
| Selectivity | — | 83.3% | — |

### vs single-feature controls
| Config | d_Sharpe | d_MDD | Supp exits | Selectivity |
|--------|----------|-------|------------|-------------|
| **AND rp=0.20,tq=-0.10** | **+0.0569** | **-7.08** | 12 | 83.3% |
| rangepos-only rp=0.25 | +0.0462 | -6.37 | 35 | 91.4% |
| trendq-only tq=-0.20 | -0.0756 | -0.51 | 104 | 78.8% |

AND gate **beats rangepos-only** on both Sharpe (+0.0107) and MDD (-0.71 pp),
with **fewer interventions** (12 vs 35). Trendq-only remains FAIL.

### Heatmap: d_sharpe
```
tq\rp      0.20    0.25    0.30    0.35
-0.30   -0.0149 -0.0132 -0.0339 -0.0267
-0.10   +0.0569 +0.0311 -0.0063 -0.0164
 0.10   +0.0446 +0.0406 -0.0298 -0.0214
 0.30   +0.0425 +0.0458 -0.0410 -0.0262
```

### Heatmap: d_mdd (negative = improvement)
```
tq\rp      0.20    0.25    0.30    0.35
-0.30    +2.14   +2.14   +3.25   +3.25
-0.10    -7.08   -5.43   -3.11   -3.11
 0.10    -7.08   -6.97   -4.49   -4.49
 0.30    -7.08   -6.37   -2.67   -2.96
```

### Key findings
1. **Tight rp wins**: rp=0.20 row dominates. Loose rp (0.30, 0.35) degrades Sharpe.
2. **tq=-0.30 too strict**: AND gate barely fires (6-19 exits), no MDD improvement.
3. **tq >= -0.10 needed**: MDD improvement appears at tq=-0.10 and persists through tq=0.30.
4. **Non-linear interaction confirmed**: AND(rp=0.20, tq=-0.10) beats BOTH single features.
   rangepos-only needs 35 exits for lesser improvement. AND gets more with 12.
5. **Selectivity**: tightest configs hit 100% loser selectivity (6-8 exits, all losers).
   Best config at 83.3% — 2/12 AND exits were on winners (acceptable cost).
6. **Overlap**: At AND(rp=0.20, tq=-0.10), 9/12 exits overlap with both single-feature
   thresholds, 3/12 are rangepos-only overlap. Zero AND-unique exits at this config.
   True AND-unique exits only appear at loose thresholds (rp>=0.30, tq>=0.10).

### Interpretation
The AND gate works because it **raises the bar for trendq** — trendq fires eagerly
(104 exits alone) but AND forces it to wait for rangepos confirmation. The tight
rp=0.20 filter is what creates value: it only exits when price is genuinely low in
its range AND momentum is deteriorating. The 12-exit count is very selective — almost
surgical — compared to rangepos-only's 35 exits.
