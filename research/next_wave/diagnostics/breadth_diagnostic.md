# D1.4 — Breadth / Regime Diagnostic Report

Date: 2026-03-07
Source: D1.2 feature store (actual BacktestEngine trades + breadth universe)
Script: `breadth_diagnostic.py`

## DIAGNOSTIC DECISION: WEAK

Breadth shows no significant signal in the full sample (MWU p=0.39, Spearman r=-0.05).
However, a conditional signal appears in the re-entry subset: re-entries during high
breadth-rank states perform significantly worse (MWU p=0.026, 80 trades). A paper veto
on this subset shows a real but narrow improvement (+$18k on 80 re-entry trades).
The signal is too subset-specific and too small-sample to justify standalone implementation.

## BREADTH_METRICS_ANALYZED

| Metric | Definition | Coverage |
|--------|-----------|----------|
| breadth_ema21_share | Fraction of 13 alts with close > H4 EMA(126) | 186/186 (100%) |
| breadth_pct_rank_90 | Percentile rank of breadth_ema21_share in rolling 90-bar window | 185/186 (99.5%) |

Breadth universe: 13 altcoins from `bars_multi_4h.csv` (BTC excluded as anchor).
D1 EMA(21) approximated as H4 EMA(126) via 6:1 bar mapping.

Note: `breadth_h4_active_share` (fraction with active X0-like state) was NOT computed.
The X0 strategy is BTC-specific; extending it to 13 alts would require per-alt backtests
that do not exist and would constitute basket construction, violating D1.4 rules.

## OUTCOME_SEPARATION_TABLES

| Variable | Mean (W) | Mean (L) | MWU p | KS p | Spearman r | Spearman p |
|----------|----------|----------|-------|------|------------|------------|
| breadth_share | 0.6107 | 0.6437 | 0.390 | 0.366 | -0.054 | 0.460 |
| breadth_pct_rank | 0.6019 | 0.6624 | 0.346 | 0.272 | -0.010 | 0.893 |

Neither metric achieves significance at any conventional level. The directional sign
(winners slightly lower breadth) is consistent with "less crowded = better" but the
effect magnitude is trivial.

## QUANTILE_EXPECTANCY_TABLES

### breadth_ema21_share (5 quintiles)

| Quintile | Range | N | Win Rate | Mean Ret% | Total PnL |
|----------|-------|---|----------|-----------|-----------|
| Q0 (lowest) | 0.00-0.31 | 39 | 48.7% | +3.41% | +$145,223 |
| Q1 | 0.33-0.54 | 40 | 47.5% | +2.27% | +$40,420 |
| Q2 | 0.58-0.77 | 37 | 45.9% | +2.50% | +$143,523 |
| Q3 | 0.82-0.92 | 33 | 45.5% | +3.48% | +$93,222 |
| Q4 (highest) | 1.00-1.00 | 37 | 40.5% | +1.97% | +$3,966 |

Win rate declines monotonically (49% -> 41%) but all quintiles have positive mean return.
PnL is non-monotonic (Q0 and Q2 both high, Q4 near zero). Kruskal-Wallis H=0.70, p=0.95
— no significant difference across quintiles.

### breadth_pct_rank_90 (4 bins, due to mass at 1.0)

| Quintile | Range | N | Win Rate | Mean Ret% | Total PnL |
|----------|-------|---|----------|-----------|-----------|
| Q0 (lowest) | 0.01-0.14 | 37 | 56.8% | +3.51% | +$128,217 |
| Q1 | 0.16-0.57 | 38 | 47.4% | +1.91% | +$31,044 |
| Q2 | 0.58-0.91 | 37 | 29.7% | +1.49% | +$49,701 |
| Q3 (highest) | 0.93-1.00 | 73 | 47.9% | +3.39% | +$217,446 |

Non-monotonic: Q0 best win rate (57%), Q2 worst (30%), Q3 recovers (48%).
The Q3 bin is large (73 trades, 39% of sample) because many entries occur when breadth
is at its local maximum. All bins positive PnL.

### Monotonicity Assessment

| Metric | Win Rate Mono | PnL Mono | Kruskal-Wallis p |
|--------|--------------|----------|-----------------|
| breadth_share | Decreasing (weak) | No | 0.952 |
| breadth_pct_rank | No | No | 0.352 |

No meaningful monotonic structure in either metric.

## PAPER_VETO_ANALYSIS

### Full sample: veto when breadth is LOW (weak market)

| Threshold | Blocked | Losers | Winners | Net PnL Effect | Remaining PnL |
|-----------|---------|--------|---------|-----------------|---------------|
| share < Q10 (0.22) | 18 | 10 | 8 | -$33,679 | $392,033 |
| share < Q20 (0.31) | 32 | 17 | 15 | -$104,801 | $321,553 |
| share < Q30 (0.45) | 55 | 31 | 24 | -$166,420 | $259,933 |

**Every low-breadth veto HURTS.** The blocked trades contain substantial winners.
Low-breadth states are actually profitable — they correspond to early trend entries
when most alts are still below their EMAs.

### Full sample: veto when breadth is HIGH

| Threshold | Blocked | Losers | Winners | Net PnL Effect | Remaining PnL |
|-----------|---------|--------|---------|-----------------|---------------|
| share > Q90 (1.00) | ~37 | ~22 | ~15 | see Q4 | see Q4 |

Q4 (breadth=1.0) has only $3,966 total PnL — near zero. But blocking 37 trades
(20% of sample) to save ~$0 is not actionable.

### Re-entry subset: veto when breadth_pct_rank is HIGH

| Threshold | Blocked | Losers | Winners | Net PnL Effect | Remaining PnL |
|-----------|---------|--------|---------|-----------------|---------------|
| pct_rank > Q50 (0.40) | 40 | 28 | 12 | +$8,046 | $65,233 |
| pct_rank > Q60 (0.58) | 32 | 23 | 9 | +$18,069 | $75,257 |
| pct_rank > Q70 (0.75) | 24 | 17 | 7 | -$9,428 | $47,760 |

**Best re-entry veto: pct_rank > Q60 (0.58), blocking 32/80 re-entries.**
Removes 23 losers vs 9 winners, net +$18,069 improvement on re-entry PnL.
Win rate improves from 46% to 58%. But:
- This is 32 trades over 7 years (4.6/year)
- Only 17% of total X0 trades
- $18k on $57k re-entry PnL — meaningful % but small absolute

## REENTRY_SUBSET_ANALYSIS

| Subset | N | Variable | MWU p | Signal? |
|--------|---|----------|-------|---------|
| Re-entry (within 6 bars) | 80 | breadth_share | 0.068 | MARGINAL |
| Re-entry (within 6 bars) | 80 | breadth_pct_rank | 0.026 | YES (conditional) |
| Non-re-entry | 106 | breadth_share | 0.619 | NO |
| Non-re-entry | 105 | breadth_pct_rank | 0.488 | NO |

**The breadth signal exists ONLY in re-entry trades.** Non-re-entry trades show
zero breadth-based separation. This mirrors the derivatives diagnostic (D1.3)
where funding signal existed only in NON-re-entry trades.

Re-entry quintile detail (breadth_pct_rank_90, 4 bins):

| Bin | N | Win Rate | Mean Ret% | Total PnL |
|-----|---|----------|-----------|-----------|
| Q0 (lowest rank) | 21 | 61.9% | +2.82% | +$56,807 |
| Q1 | 19 | 63.2% | +2.49% | +$8,427 |
| Q2 | 21 | 23.8% | -1.14% | -$27,665 |
| Q3 (highest rank) | 19 | 36.8% | +0.76% | +$19,620 |

Win rate drops sharply from Q0-Q1 (62%) to Q2 (24%), then partially recovers in Q3 (37%).
The Q2 trough is the main driver of the signal. Non-monotonic structure.

## POST_STOP_SUBSET_ANALYSIS

| Subset | N | Variable | MWU p | Signal? |
|--------|---|----------|-------|---------|
| Post-stop | 172 | breadth_share | 0.281 | NO |
| Post-stop | 172 | breadth_pct_rank | 0.418 | NO |
| Post-trend-exit | 13 | both | N/A | INSUFFICIENT DATA |

No breadth signal in post-stop trades (which are 92% of all trades).

## DERIVATIVES_VS_BREADTH_COMPARISON

| Property | Breadth (share) | Funding (raw) |
|----------|----------------|---------------|
| Spearman r vs outcome | -0.054 | -0.197 |
| Spearman p vs outcome | 0.460 | 0.011 |
| Coverage | 186/186 | 165/186 |
| Signal subset | Re-entry only | Non-re-entry only |
| Paper veto (full sample) | ALL HURT | ALL HURT/BREAK EVEN |
| Paper veto (conditional) | +$18k (re-entry) | ~$0 (Q95) |

### Orthogonality

Breadth-Funding Spearman r = 0.239 (p=0.002). Modest positive correlation —
breadth and funding are partially correlated (when breadth is high, funding tends
to be higher). Not fully orthogonal, but not redundant.

### Complementarity

The two signals are structurally complementary:
- **Funding**: significant in non-re-entry trades (MWU p=0.009), dead in re-entries
- **Breadth**: significant in re-entry trades (MWU p=0.026), dead in non-re-entries

Together they could cover both subsets — but each individual signal is weak/conditional.

### Assessment

| Criterion | Breadth | Funding | Winner |
|-----------|---------|---------|--------|
| Raw signal strength | Weaker | Stronger | Funding |
| Coverage (no NaN) | Better | Worse | Breadth |
| Robustness (full sample) | FAIL | WEAK | Funding |
| Conditional signal | YES (re-entry) | YES (non-re-entry) | TIE |
| Paper veto actionable | Marginal | No | Breadth (barely) |
| Trade count impact | Moderate (blocks 17%) | Minimal | TIE |

Neither is strong enough standalone. Combined coverage is interesting but
adds complexity for marginal gain.

## Incremental Information

| Variable | vs Outcome r | vs VDO r | vs bars_since_exit r |
|----------|-------------|----------|---------------------|
| breadth_share | -0.054 | -0.041 | -0.001 |
| breadth_pct_rank | -0.010 | +0.195 | +0.387 |

breadth_ema21_share is independent of existing context variables (near-zero correlation).
breadth_pct_rank_90 is substantially correlated with bars_since_exit (r=0.39) — partial
confounding. Some of the "breadth rank" signal in re-entries may be timing in disguise.

## Concentration

| Metric | Worst 20% in weak breadth | Worst 20% in strong breadth | Expected (uniform) |
|--------|--------------------------|----------------------------|--------------------|
| breadth_share | 5/37 (13.5%) | 15/37 (40.5%) | 7.4/37 (20%) |
| breadth_pct_rank | 6/37 (16.2%) | 9/37 (24.3%) | 7.4/37 (20%) |

**Worst trades concentrate in STRONG breadth, not weak breadth.** This is the opposite
of a "weak breadth = danger" hypothesis. 15/37 worst trades occurred at breadth=Q80+.
This undermines the case for a low-breadth veto on the full sample.

Best trades show no concentration (near uniform across breadth states).

## DIAGNOSTIC_DECISION

**WEAK** — breadth shows:
1. No significant signal in the full sample (p=0.39)
2. A conditional signal in re-entry trades only (p=0.026, N=80)
3. Non-monotonic quintile structure (Q2 trough, Q3 recovery)
4. Paper veto on full sample always hurts (low-breadth states are profitable)
5. A marginal paper veto improvement in the re-entry subset only (+$18k)
6. Partial confounding of breadth_pct_rank with bars_since_exit (r=0.39)
7. Worst trades concentrate in strong breadth (opposite of expected)

## IF_PASS_SINGLE_BEST_CANDIDATE

IF a later diagnostic (e.g., combined breadth + funding gate for re-entries)
justifies a multi-signal conditional veto, the single best breadth candidate is:

- **Variable**: breadth_pct_rank_90
- **Subset**: re-entry trades only (within 6 bars of prior exit)
- **Direction**: higher pct_rank = worse re-entry outcomes
- **Candidate threshold**: pct_rank > 0.58 (Q60 of re-entry distribution)
- **Effect**: blocks 32/80 re-entries, 23 losers / 9 winners, +$18k net

This is pre-registered as a CONDITIONAL candidate. It must NOT be implemented
standalone — the signal is too narrow (80 trades, one subset, p=0.026 before
any multiple-testing correction).

## RISKS_OF_FALSE_DISCOVERY

1. **Multiple testing**: 2 breadth metrics × 2 subsets = 4 effective tests.
   The best p-value (0.026) would not survive Bonferroni correction (adjusted p=0.104).

2. **Small conditional sample**: 80 re-entry trades is a fragile basis.
   The Q2 trough (21 trades, 24% win rate) drives most of the signal.
   A few different trades could eliminate the pattern.

3. **Confounding with timing**: breadth_pct_rank correlates with bars_since_exit
   (r=0.39) — some signal may be re-entry timing in disguise, not breadth per se.

4. **Non-monotonic structure**: The Q3 recovery (37% WR, positive PnL) breaks
   the "high breadth = bad" narrative. The signal is concentrated in Q2, not broadly
   distributed across high-breadth states.

5. **Worst-trade concentration contradicts theory**: If weak breadth were dangerous,
   worst trades should cluster there. They cluster in STRONG breadth instead.

6. **Full-sample paper veto failure is decisive**: Even if the conditional signal
   is real, the full-sample veto always hurts. Any implementation must be
   subset-conditional (re-entry only), adding complexity for marginal gain.

7. **Complementarity with funding is appealing but unproven**: The breadth-reentry +
   funding-non-reentry pattern is elegant, but combining two WEAK/marginal signals
   does not produce a STRONG composite without further validation.
