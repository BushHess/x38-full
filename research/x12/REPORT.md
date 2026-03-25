# X12: Why Does E5 Win If It Doesn't Fix Churn? — Report

**Date**: 2026-03-09
**Verdict**: CHURN_FAILS_BUT_TAIL_WINS (E5-E0 gap is noise)

## Central Question

E5 (robust ATR) doesn't reduce churn rate (64.5% vs 63.1%). So where does its
headline NAV advantage come from?

## Results

### T0: Churn Audit

| Metric | E0 | E5 | Delta |
|--------|----|----|-------|
| Total trades | 186 | 199 | +13 |
| Trail stop exits | 168 | 183 | +15 |
| Churn count | 106 | 118 | +12 |
| Churn rate | 63.1% | 64.5% | +1.4pp |
| Churn PnL | +$329,680 | +$423,372 | +$93,692 |
| Non-churn trail PnL | -$128,136 | -$154,894 | -$26,758 |

Key insight: churn exits have **positive** total PnL in both E0 and E5.
The losers are the non-churn trail exits (genuine reversals).

### T1: Cascade Map

- 169 matched trades, 17 E0-only, 30 E5-only
- 101 matched with same exit: mean PnL delta = +$48 (negligible)
- 68 matched with different exit: mean PnL delta = +$645 (E5 exits later/better)
- 27 cascade events (one exit triggers another), max depth 4

### T2: Matched Mechanism

- Of 68 different-exit trades: E5 exits first in 61 cases, E0 in 7
- E5 wins PnL in 45/68 cases (66%)
- Duration buckets: long trades benefit most (mean d_pnl = +$1,442)
- Winners improve more than losers (E5 makes winners bigger)

### T3: Decomposition

| Component | PnL | Return % |
|-----------|-----|----------|
| Headline delta | +$60,460 | — |
| Matched trades delta | +$48,696 (81%) | +13.0% |
| Cascade delta | +$11,764 (19%) | +11.4% |
| Residual | ~0 | — |
| Churn-fix fraction (PnL) | 0.19% | — |
| Churn-fix fraction (return) | 0.47% | — |

E5's edge comes from **path-state** (smoother ATR → different exit timing),
NOT from churn repair. Churn-fix explains <0.5% of the return delta.

### T4: Timescale Stability

- Churn pattern stable across 15/16 timescales
- Counterfactual stable across 12/16 timescales
- G3: PASS

### T5: Bootstrap

| Metric | Value |
|--------|-------|
| Headline delta median | -$331 |
| P(headline > 0) | 46.4% |
| cf_ret median | -0.007% |
| P(cf_ret > 0.5%) | 35.0% |
| d_churn median | +1.6pp |
| P(d_churn < 0) | 22.2% |

**E5-E0 headline gap is NOISE** (P=46.4%, below 50% chance of being positive).
The real-data gap of +$60K is well within bootstrap confidence interval.

### T6: Cost Sweep

- Crossover at ~38 bps RT
- Below 38 bps: E5 has edge (smoother ATR = fewer whipsaws at low cost)
- Above 38 bps: neutral (at harsh 50 bps, both similar)

## Conclusions

1. **E5 does NOT fix churn** — churn rate slightly increases (63.1% → 64.5%)
2. **Churn exits are net profitable** in both E0 and E5 (counterintuitive)
3. **E5-E0 gap = noise** (bootstrap P=46.4%) — path-state mechanism, not churn repair
4. **E5's real advantage**: smoother ATR → different exit timing on matched trades
5. **Cost crossover at 38 bps**: E5 better at low cost, neutral at high cost

## Verdict: CHURN_FAILS_BUT_TAIL_WINS

E5's robust ATR doesn't fix churn — it changes exit timing through smoother
ATR estimates. The headline NAV advantage is statistically indistinguishable
from zero at current sample size. The churn problem remains open for a dedicated filter approach.

> **Supersession note (2026-03-13)**: Original text used "noise" for the E5-E0 gap.
> Corrected characterization: **inconclusive** (P=46.4%, direction ambiguous) with
> **cost-dependent value** (crossover at 38 bps, see X22). Per methodology.md §8c,
> "underpowered" and "inconclusive" are the correct terms.

## Artifacts

- `x12_results.json` — all test results
- `x12_churn_audit.csv`, `x12_cascade.csv`, `x12_mechanism.csv`
- `x12_decomposition.csv`, `x12_bootstrap.csv`, `x12_cost_sweep.csv`
