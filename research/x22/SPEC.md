# X22: Cost Sensitivity Analysis — Strategy Robustness to Execution Cost

## Context

ALL 53 prior studies use 50 bps RT (harsh cost assumption). This was deliberate —
if a strategy works at 50 bps, it works at any realistic cost.

Real-world BTC execution costs (2026):
- Binance maker: ~2-4 bps RT
- Binance taker: ~14-20 bps RT
- Smart routing (maker+limit): ~8-15 bps RT
- Institutional (OTC, dark pool): ~5-10 bps RT

The 50 bps assumption is **3-10× harsher** than reality. This creates a large gap
between research performance and expected live performance.

### Why This Study Matters

1. **Performance forecast**: What Sharpe/CAGR to expect at realistic costs?
2. **Churn filter value**: X18/X14D add +0.09-0.15 Sharpe at 50 bps. Do they
   still add value at 15 bps? Churn filter reduces trade count — its value is
   proportional to cost.
3. **Strategy ranking**: Does the relative ranking of strategies change at
   realistic costs? E5 might become unnecessary if cost savings dominate.
4. **Breakeven cost**: At what cost does each strategy become negative-EV?

### Prior Cost Evidence

Study #9 (position_sizing.py): tested only at 50 bps.
Study #43 (E5+EMA1D21 eval): tested only at 50 bps.
All churn studies (X12-X19): tested only at 50 bps.
**Zero studies explore cost sensitivity.** This is a gap.

## Central Question

How do strategy metrics (Sharpe, CAGR, MDD) vary as a function of execution cost?
At what cost does the churn filter become unnecessary? What performance should we
expect at realistic costs (10-20 bps)?

## Architecture

### This is a CHARACTERIZATION study, not an optimization study.

No new parameters. No new DOF. No gates to pass. The output is a set of curves
and tables that inform production decisions.

### Strategy Set

4 strategies, ordered by complexity:

| Strategy | DOF | Description |
|----------|-----|-------------|
| E0 | 3 | Baseline: EMA entry + ATR trail + EMA exit |
| E5+EMA1D21 | 4.35 | Primary: robust ATR + EMA regime filter |
| E5+EMA1D21+X14D | 5.35 | + churn filter P>0.5 (risk-focused) |
| E5+EMA1D21+X18 | 5.35 | + churn filter α=40% (return-focused) |

### Cost Sweep

```
cost_bps ∈ {2, 5, 10, 15, 20, 25, 30, 40, 50, 75, 100}  (11 values)
```

This covers:
- 2 bps: theoretical best (maker-maker)
- 5-15 bps: realistic smart execution range
- 20-30 bps: conservative realistic range
- 50 bps: current research assumption
- 75-100 bps: stress test / adversarial

### Total backtests: 4 strategies × 11 costs = 44

## Data

Same as all BTC studies:
- `data/bars_btcusdt_2016_now_h1_4h_1d.csv`
- Period: 2017-08 to 2026-02
- H4 primary, D1 for regime filter
- Default params: N=120, trail=3.0, VDO=0.0, EMA=21d

## Test Suite

### T0: Full Metric Table

For each strategy × cost combination, compute:
- Sharpe, CAGR (%), MDD (%), Calmar
- Total trades, trade frequency (trades/year)
- Total cost drag (bps/year) = cost_bps × trades / years
- Final NAV

**Output**: 44-row table (4 strategies × 11 costs).

### T1: Breakeven Analysis

For each strategy, find the cost at which:
- Sharpe = 0
- CAGR = 0
- Sharpe < buy-and-hold Sharpe

**Method**: Interpolate between cost points.

**Output**: Breakeven table (4 strategies × 3 breakeven types).

### T2: Churn Filter Marginal Value

For each cost level:
- d_sharpe_X18 = Sharpe(E5+EMA1D21+X18) - Sharpe(E5+EMA1D21)
- d_sharpe_X14D = Sharpe(E5+EMA1D21+X14D) - Sharpe(E5+EMA1D21)
- d_cagr_X18, d_cagr_X14D (same for CAGR)

**Key output**: The cost at which d_sharpe → 0 (churn filter becomes worthless).

Theoretical prediction:
- Churn filter reduces trades from ~226 to ~133-147
- Cost savings per year ≈ (226-K) × cost_bps / 8.5 years
- At 50 bps: savings = 79 × 50 / 8.5 ≈ 465 bps/year
- At 10 bps: savings = 79 × 10 / 8.5 ≈ 93 bps/year
- At 2 bps: savings = 79 × 2 / 8.5 ≈ 19 bps/year

If churn filter value is MOSTLY from cost savings (vs genuine alpha from holding
through churn), then d_sharpe should decrease roughly linearly with cost.

If churn filter value is MOSTLY from alpha (genuine continuation capture), then
d_sharpe should be relatively stable across costs.

**This test disambiguates the source of churn filter alpha.**

### T3: Strategy Ranking at Realistic Costs

At cost = {10, 15, 20} bps:
- Rank strategies by Sharpe
- Rank strategies by CAGR
- Rank strategies by Calmar
- Does the ranking change from the 50 bps ranking?

If E5+EMA1D21 (without churn filter) beats churn filter variants at low cost →
churn filter is cost-dependent, not a genuine alpha source.

### T4: Bootstrap at Realistic Cost (500 VCBB)

Run full bootstrap at cost = 15 bps (realistic smart execution):
- For each strategy: 500 VCBB paths
- Report: median Sharpe, P(Sharpe > 0), median CAGR, P(CAGR > 0)
- Compare with 50 bps bootstrap results from prior studies

This provides the EXPECTED live performance distribution.

### T5: Cost Drag Decomposition

For each strategy at 50 bps:
- Total cost drag = trades × 50 bps = X bps total
- Annualized: X / years = Y bps/year
- As fraction of gross CAGR: Y / (CAGR + Y)

**Question**: What fraction of gross alpha is consumed by cost at 50 bps vs 15 bps?

## Output Specification

### Primary deliverables

1. **Cost sensitivity curves**: 4 curves (one per strategy) plotting Sharpe vs cost
2. **Churn filter value curve**: d_sharpe vs cost for X18 and X14D
3. **Breakeven table**: cost at which each strategy breaks even
4. **Realistic performance table**: metrics at 10, 15, 20 bps
5. **Bootstrap distribution at 15 bps**: histogram of Sharpe and CAGR

### Decision support (not gates — recommendations)

| Finding | Recommendation |
|---------|---------------|
| Churn filter value stable across costs | Churn filter captures genuine alpha → deploy with filter |
| Churn filter value → 0 below 20 bps | Churn filter is cost-dependent → may skip filter in production |
| E0 beats E5+EMA1D21 at low cost | E5's value is cost savings, not signal quality → reconsider |
| All strategies Sharpe > 2.0 at 15 bps | Strong case for aggressive deployment |

## Implementation Notes

### Minimal code change required

The sim already takes `cps` as a parameter. The only change is to sweep
`cps` across values instead of fixing at 0.0025.

```python
for strategy in strategies:
    for cost_bps in [2, 5, 10, 15, 20, 25, 30, 40, 50, 75, 100]:
        cps = cost_bps / 20_000.0  # per-side
        result = run_backtest(strategy, cps=cps)
```

### Churn filter integration

For X18 and X14D runs: reuse the trained churn model from X14/X18 studies.
Model is cost-independent (trained on labels, not returns). Only the SIM
is re-run at different costs.

### Bootstrap at 15 bps

Same VCBB machinery as all prior studies. Only change: `cps = 0.00075`
instead of `cps = 0.0025`.

## Estimated Runtime

- T0 (44 backtests): ~15s
- T1 (breakeven): ~1s (interpolation)
- T2 (churn value): ~1s (arithmetic on T0 results)
- T3 (ranking): ~1s (sorting T0 results)
- T4 (bootstrap 15 bps): ~120s (500 paths × 4 strategies)
- T5 (decomposition): ~1s
- Total: ~2.5 min

## Output Files

```
x22/
  SPEC.md
  benchmark.py
  x22_results.json
  x22_full_table.csv       (T0: 44 rows)
  x22_breakeven.csv        (T1)
  x22_churn_value.csv      (T2)
  x22_ranking.csv          (T3)
  x22_bootstrap_15bps.csv  (T4)
  x22_cost_decomp.csv      (T5)
  REPORT.md
```
