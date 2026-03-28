# Exp 52: Vol Compression at Realistic Costs

## Status: DONE

## Hypothesis
All x39 experiments use 50 bps RT (harsh). X22 (cost sensitivity research)
showed that mechanisms are COST-DEPENDENT: churn filters HURT at <30 bps
because they remove trades that are profitable at lower costs.

Vol compression (exp34/42) is a WFO-validated entry filter. But its value
may differ at realistic costs:
- Binance VIP0 + BNB: ~15 bps RT
- Binance VIP1: ~20 bps RT
- Harsh (current): 50 bps RT

At lower costs, more entries are profitable → blocked entries may have
HIGHER win rate → selectivity may weaken. If compression's selectivity
disappears at realistic costs → it's a cost-reduction mechanism (blocks
entries that only lose because of high costs), not a genuine quality filter.

If selectivity persists at 15-25 bps → compression captures genuine
entry quality information independent of cost model.

This experiment characterizes vol compression across the cost spectrum.

## Baseline
E5-ema21D1 (simplified replay) at each cost level.

## Cost levels
[10, 15, 20, 25, 30, 40, 50] bps RT

## Configurations per cost level
- Baseline (no compression): each cost level
- Threshold=0.6: each cost level
- Threshold=0.7: each cost level
- (3 × 7 = 21 runs)

## What to measure

Per cost × config:
- Sharpe, CAGR%, MDD%, trades, win_rate
- d_Sharpe vs baseline at same cost
- Blocked entries and blocked WR at each cost level

Key analysis:
1. **d_Sharpe vs cost curve**: does compression's delta increase, stay flat,
   or decrease as cost decreases?
   - Increasing: compression is a cost reducer (more value at high cost)
   - Flat: genuine quality filter (value independent of cost)
   - Decreasing: mechanism is cost-dependent (like churn filters in X22)

2. **Selectivity vs cost**: blocked WR - baseline WR at each cost.
   - If selectivity weakens at low cost → cost-dependent mechanism
   - If selectivity persists → genuine quality filter

3. **Breakeven cost**: at what cost level does compression stop helping?
   (d_Sharpe crosses zero)

4. **Optimal threshold vs cost**: is thr=0.7 optimal at all costs,
   or does the optimal threshold shift with cost level?

## Connection to X22 findings
X22 showed E5-ema21D1 at 15 bps has Sharpe 1.670, CAGR 75%. Adding
compression at 15 bps should show:
- If compression adds ~+0.19 Sharpe (same as at 50 bps) → cost-independent
- If compression adds less → cost-dependent value
- If compression hurts → DO NOT deploy at realistic costs

## Implementation notes
- Simple cost model: cost = cost_bps / 10_000 deducted from each round trip
- Use same backtest framework as exp34
- Only vary cost_bps parameter across runs
- No WFO needed here — exp42 already validated temporal stability.
  This is a characterization study at different cost points.
- Warmup: 365 days (same as exp34)

## Output
- Script: x39/experiments/exp52_compression_realistic_costs.py
- Results: x39/results/exp52_results.csv

## Result

**VERDICT: COST-INDEPENDENT — Genuine quality filter**

Vol compression helps at ALL 7 cost levels (10-50 bps). Unlike churn filters
(X22), compression is NOT a cost-reduction mechanism.

### d_Sharpe vs Cost (threshold=0.6)

| Cost (bps) | Baseline Sh | +Compression Sh | d_Sharpe | d_MDD (pp) |
|:----------:|:-----------:|:----------------:|:--------:|:----------:|
| 10 | 1.5539 | 1.7249 | +0.1710 | +2.71 |
| 15 | 1.5216 | 1.6950 | +0.1734 | +2.66 |
| 20 | 1.4893 | 1.6652 | +0.1759 | +2.59 |
| 25 | 1.4571 | 1.6353 | +0.1782 | +2.54 |
| 30 | 1.4249 | 1.6055 | +0.1806 | +2.49 |
| 40 | 1.3606 | 1.5460 | +0.1854 | +2.37 |
| 50 | 1.2965 | 1.4866 | +0.1901 | +2.27 |

### d_Sharpe vs Cost (threshold=0.7)

| Cost (bps) | Baseline Sh | +Compression Sh | d_Sharpe | d_MDD (pp) |
|:----------:|:-----------:|:----------------:|:--------:|:----------:|
| 10 | 1.5539 | 1.7194 | +0.1655 | +0.69 |
| 15 | 1.5216 | 1.6889 | +0.1673 | +0.65 |
| 20 | 1.4893 | 1.6585 | +0.1692 | +0.61 |
| 25 | 1.4571 | 1.6281 | +0.1710 | +0.58 |
| 30 | 1.4249 | 1.5977 | +0.1728 | +0.55 |
| 40 | 1.3606 | 1.5370 | +0.1764 | +0.48 |
| 50 | 1.2965 | 1.4764 | +0.1799 | +0.42 |

### Key Findings

1. **d_Sharpe vs cost**: Weakly INCREASING (ratio 15bps/50bps = 0.91-0.93).
   Delta is ~91% as large at 15 bps as at 50 bps → nearly cost-independent.
   Slight increase at higher cost = minor cost-reduction component on top of
   genuine quality filtering.

2. **Selectivity persists at ALL costs**: Blocked WR < baseline WR at every
   cost level (e.g., 38.0% vs 43.9% at 15 bps for thr=0.6). Gap is stable
   (~5-7 pp) regardless of cost → genuine entry quality signal.

3. **No breakeven**: d_Sharpe > 0 at ALL costs for both thresholds. Compression
   never hurts, unlike churn filters which hurt below ~30 bps.

4. **Optimal threshold stable**: thr=0.6 wins at ALL 7 cost levels. No shift
   in optimal threshold with cost.

5. **MDD trade-off**: thr=0.6 adds +2.3-2.7 pp MDD. thr=0.7 much better at
   +0.4-0.7 pp MDD with only ~0.01 less d_Sharpe.

### Contrast with X22 (Churn Filters)

| Mechanism | Value at 15 bps | Value at 50 bps | Cost-dependent? |
|:---------:|:---------------:|:---------------:|:---------------:|
| Churn filters (X22) | HURTS | HELPS | YES |
| Vol compression (exp52) | +0.173 Sharpe | +0.190 Sharpe | NO (~91% retained) |

**Conclusion**: Vol compression captures genuine entry quality information.
At realistic costs (15-25 bps), deploy compression WITHOUT churn filter.
