# Exp 52: Vol Compression at Realistic Costs

## Status: PENDING

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
_(to be filled by experiment session)_
