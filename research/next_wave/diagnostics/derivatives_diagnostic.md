# D1.3 — Derivatives Crowded-State Diagnostic Report

Date: 2026-03-07
Source: actual BacktestEngine trades + Binance Futures API data
Script: `derivatives_diagnostic.py`

## DIAGNOSTIC DECISION: WEAK

Funding rate shows a real but modest signal (Spearman r=-0.20, MWU p=0.032).
Basis shows no usable signal (MWU p=0.617). OI was excluded (only 83 recent records).
No paper veto threshold improves total PnL. No derivatives overlay should be built now.

## Data Coverage

| Variable | Records | Range | Coverage of 186 X0 entries |
|----------|---------|-------|---------------------------|
| Funding rate (8h) | 7,067 | 2019-09-10 to 2026-02-20 | 165/186 (88.7%) |
| Perp H4 klines | 14,145 | 2019-09-08 to 2026-02-21 | 165/186 (88.7%) |
| Open interest | 83 | 2026-02-07 to 2026-02-21 | EXCLUDED |

21 entries pre-date Binance Futures launch (Sep 2019).

## Outcome Separation

| Variable | Mean (W) | Mean (L) | MWU p | KS p | Spearman r | Spearman p |
|----------|----------|----------|-------|------|------------|------------|
| funding_raw | 0.000094 | 0.000130 | 0.032 | 0.071 | -0.197 | 0.011 |
| funding_pct_rank_30d | 0.429 | 0.543 | 0.013 | 0.041 | -0.220 | 0.005 |
| basis_pct | -0.006 | +0.001 | 0.617 | 0.774 | -0.116 | 0.139 |

Funding pct_rank is the strongest separator (lower rank = more winners).

## Quintile Expectancy (funding_pct_rank_30d)

| Quintile | Range | N | Win Rate | Mean Ret% | Total PnL |
|----------|-------|---|----------|-----------|-----------|
| Q0 (lowest) | 0.01-0.19 | 34 | 55.9% | +5.21% | +$154,426 |
| Q1 | 0.19-0.41 | 32 | 53.1% | +1.73% | +$125,056 |
| Q2 | 0.42-0.58 | 33 | 48.5% | +3.35% | +$121,505 |
| Q3 | 0.59-0.80 | 33 | 36.4% | +1.14% | +$28,725 |
| Q4 (highest) | 0.81-1.00 | 33 | 30.3% | +0.33% | -$17,259 |

Win rate declines monotonically (56% → 30%). Mean return mostly declines but Q2 spikes.
Only Q4 has negative total PnL. Broad-based or concentrated? The Q4 losses are
spread across 33 trades over multiple years — not concentrated in a single episode.

## Paper Veto Summary

**Every tested veto threshold hurts or breaks even.** The signal is too weak
to offset the cost of blocking winners.

Best case: funding_raw > 0.000438 (Q95) blocks 9 trades (7 losers, 2 winners)
for a net effect of -$1,958 — essentially zero.

## Subset Analysis

| Subset | N | Funding MWU p | Signal Present? |
|--------|---|---------------|-----------------|
| Re-entry (within 6 bars) | 71 | 0.897 | NO |
| Non-re-entry | 94 | 0.009 | YES |
| Post-stop | 153 | 0.027 | YES (weaker) |
| Post-trend-exit | 12 | N/A | insufficient data |

The funding signal exists only in non-re-entry trades. Re-entry trades
show zero funding-based separation.

## Concentration

Worst 20% of trades do NOT cluster in extreme funding or basis states.
Distribution of worst/best trades across extreme states is consistent
with uniform (within ±2-7% of expected 20%).

## Incremental Information

- funding_raw vs outcome: r=-0.197 (modest, p=0.011)
- vdo vs outcome: r=0.081 (not significant, p=0.300)
- bars_since_exit vs outcome: r=-0.017 (not significant, p=0.830)
- funding adds information beyond context vars
- But funding is correlated with bars_since_exit (r=-0.28) — partial confounding

## Effect Classification

- Funding rate: **WEAK, broad-based** (spread across years, not artifact-driven,
  but too small magnitude to survive veto cost)
- Basis: **FAIL** (no separation at any level)
- OI: **EXCLUDED** (insufficient data)

## Pre-Registration (conditional)

IF a later diagnostic (e.g., combined with breadth) justifies a multi-signal gate,
the single best derivatives candidate is:
- Variable: **funding_pct_rank_30d**
- Normalization: percentile rank within rolling 90-event window
- Direction: lower pct_rank = better trades (less crowded = better)

## Risks of False Discovery

1. 165 trades is a small sample — MWU p=0.032 would not survive Bonferroni
   correction across 3 variables tested (adjusted p=0.096)
2. The Q2 spike in quintile table breaks monotonicity — fragile structure
3. Partial confounding with bars_since_exit means some "funding signal" may be
   re-entry timing in disguise
4. Paper veto failure is the decisive evidence: even if the signal is real,
   it is not actionable as a standalone veto
