# D1.5 — Conditional Re-entry / State Divergence Diagnostic Report

Date: 2026-03-07
Source: D1.2 feature store (actual BacktestEngine trades), D1.3/D1.4 derived features
Script: `reentry_diagnostic.py`

## DIAGNOSTIC DECISION: WEAK

Re-entries are net profitable ($57K over 80 trades) but earn 4.9x less PnL/trade than
non-re-entries. The gap is driven entirely by **smaller winners** (53% of non-re winner
size), not by more or larger losses. Win rates and loser sizes are nearly identical.

One narrow conditional rule shows promise: veto re-entry within 2 bars when
breadth_ema21_share > 0.80 (blocks 15 trades, 12L/3W, +$24K net). But 15 trades
over 7 years is a fragile basis for any rule.

## REENTRY_TRADE_DEFINITION_TABLE

| Threshold | N Re-entry | % of 186 | WR Re | WR Non-Re | MeanRet Re | MeanRet Non | MWU p |
|-----------|-----------|----------|-------|-----------|------------|-------------|-------|
| 1 bar | 30 | 16.1% | 50.0% | 44.9% | +1.00% | +3.04% | 0.797 |
| 2 bars | 47 | 25.3% | 46.8% | 45.3% | +1.26% | +3.20% | 0.950 |
| 3 bars | 56 | 30.1% | 48.2% | 44.6% | +1.30% | +3.32% | 0.869 |
| 4 bars | 66 | 35.5% | 50.0% | 43.3% | +1.18% | +3.56% | 0.792 |
| 6 bars | 80 | 43.0% | 46.2% | 45.3% | +1.22% | +3.84% | 0.995 |

No definition threshold produces a statistically significant difference in returns
(all MWU p > 0.79). Win rates are consistently similar or slightly HIGHER for
re-entries. The mean return gap is entirely from winner magnitude, not win rate.

Primary definition used throughout: **within 6 bars** (43% of trades, consistent
with D1.3 and D1.4).

## REENTRY_VS_NONREENTRY_EXPECTANCY

| Metric | Re-entry (80) | Non-re-entry (106) | Difference |
|--------|--------------|-------------------|------------|
| Win rate | 46.2% | 45.3% | +1.0pp |
| Mean return | +1.22% | +3.84% | -2.63pp |
| Total PnL | +$57,188 | +$369,166 | -$312K |
| PnL/trade | $715 | $3,483 | -$2,768 |
| Avg winner PnL | $7,116 | $13,370 | 53% |
| Avg loser PnL | -$4,793 | -$4,700 | ~same |
| MWU p | — | — | 0.995 |

### Key decomposition

The PnL/trade gap comes from **smaller winners, not worse losses:**
- Re-entry winners average $7,116 vs non-re-entry winners $13,370 (53% of size)
- Re-entry losers average -$4,793 vs non-re-entry losers -$4,700 (essentially equal)
- Win rates are similar (46.2% vs 45.3%)

**Why smaller winners?** Re-entries catch trend continuations closer to the trailing
stop. Even when they win, the continuation is shorter. This is structural — it's a
property of where in the trend cycle re-entries occur, not a bug.

### Bootstrap test

95% CI for PnL/trade difference (re - nre): [-$6,439, +$611]
P(re worse than nre) = 94.4% — consistent direction but NOT significant at 95%.

### Would removing all re-entries help?

**No.** Removing all 80 re-entries loses $57,188 of net positive PnL. Re-entries
are net profitable; the question is whether SPECIFIC re-entries can be selectively
vetoed.

## CONTEXTUAL_CLUSTERING_ANALYSIS

### Breadth clustering (within re-entries)

| Context | Losers (N=43) | Winners (N=37) | Concentration? |
|---------|--------------|----------------|----------------|
| Low breadth (Q20, <= 0.31) | 8 (19%) | 10 (27%) | MORE winners in low |
| Mid breadth | 25 (58%) | 22 (59%) | uniform |
| High breadth (Q80, >= 0.92) | 10 (23%) | 5 (14%) | MORE losers in high |

Re-entry losers cluster modestly in **high breadth** states (23% vs 14% for winners).
This is consistent with D1.4's finding that breadth_pct_rank separates re-entry outcomes.

Mean breadth: losers 0.6277 vs winners 0.5544 — losers enter in slightly higher breadth.

### Breadth pct_rank clustering

Mean pct_rank: losers 0.5750 vs winners 0.3742 — losers enter when breadth is
relatively elevated vs recent history. This confirms D1.4.

### Funding clustering

| Context | Losers (N=39) | Winners (N=32) | Concentration? |
|---------|--------------|----------------|----------------|
| High funding rank (Q80) | 13 (33%) | 2 (6%) | STRONG loser concentration |

**13/39 re-entry losers** (33%) occur in high funding states vs only **2/32 winners**
(6%). This is a strong asymmetry — but it was NOT significant in D1.3's re-entry
subset analysis (MWU p=0.897). The discrepancy may be because MWU tests distribution
shape while this tests tail clustering.

Mean funding rank: losers 0.6875 vs winners 0.6068 — modest difference.

### VDO clustering

| Context | Losers (N=43) | Winners (N=37) |
|---------|--------------|----------------|
| Low VDO (Q20) | 12 (28%) | 11 (30%) |
| High VDO (Q80) | 6 (14%) | 2 (5%) |

No meaningful clustering. VDO does not discriminate re-entry outcomes.

### Exit reason clustering

| Prior exit | N re-entries | Win rate |
|-----------|-------------|----------|
| Trail stop | 78 | 46.2% |
| Trend exit | 2 | 50.0% |

97.5% of re-entries follow a trail stop (by construction — trend exits are rare).
The 2 post-trend re-entries are too few for analysis.

### BSE granularity within re-entries

| Within N bars | N | Win Rate | Mean Ret | PnL |
|--------------|---|----------|----------|-----|
| 1 | 30 | 50.0% | +1.00% | +$72,658 |
| 2 | 47 | 46.8% | +1.26% | +$51,947 |
| 3 | 56 | 48.2% | +1.30% | +$55,716 |

Immediate re-entries (1 bar) have higher win rate (50%) and higher PnL than broader
re-entry groups. The incremental trades from 2-6 bars are net dilutive.

## STATE_DIVERGENCE_RELEVANCE

### X0 vs Anchor (E0_EMA21) trade comparison

| Metric | X0 | Anchor | Difference |
|--------|-----|--------|------------|
| Total trades | 186 | 172 | +14 |
| Shared entries | 157 | 157 | — |
| X0-only entries | 29 | — | new from different exits |
| Anchor-only entries | — | 15 | new from different exits |
| Total PnL | $426,354 | $325,924 | +$100,431 |

### PnL advantage attribution

X0's $100K advantage over anchor decomposes into three sources:

| Source | PnL Contribution | Trades | Notes |
|--------|-----------------|--------|-------|
| X0-only trades (new entries) | +$43,411 | 29 (27 re-entries) | 55% WR |
| Avoided anchor-only trades | +$4,086 | 15 avoided | Anchor-only had -$4K PnL |
| Different exits on shared trades | +$52,933 | 62/157 shared had diff exits | Robust ATR exits differ |

### Re-entry path contribution

**27/29 X0-only trades are re-entries.** These are trades that exist in X0 but not in
the anchor, because X0's different trailing stop (robust ATR) creates different exit
timing, which shifts re-entry opportunities.

- X0-only re-entries: $43,411 PnL, 55% win rate — net profitable, net additive
- Without these, X0's advantage would shrink from $100K to $57K

**Conclusion:** The altered re-entry path from robust ATR is a meaningful part of X0's
advantage. Re-entries are not just noise — they capture real post-stop continuation
opportunities that the standard ATR exit misses.

### Do post-stop re-entries contribute disproportionate pain?

| Question | Answer |
|----------|--------|
| Are re-entries overrepresented in worst 20%? | 17/37 (46%) vs 43% overall — barely |
| Are re-entries overrepresented in best 20%? | 15/37 (41%) vs 43% overall — barely |
| Is the re-entry worst-trade distribution special? | No — nearly uniform |

Re-entries do NOT contribute disproportionate pain. Their representation in worst/best
trade tails is consistent with their overall prevalence.

### Worst 10 re-entries

- Total PnL: -$112,340 (vs +$57K total re-entry PnL)
- Mean breadth: 0.6231 (vs 0.5767 overall)
- Mean BSE: 2.2 bars
- Years: 2022(3), 2024(3), 2025(2), 2023(1), 2026(1) — spread across time
- No temporal clustering — worst re-entries are distributed, not episodic

## PAPER_RULE_ANALYSIS

Three narrow conditional re-entry rules tested:

### Rule 1: re6_breadth_rank_gt_0.58
**Veto re-entry within 6 bars when breadth_pct_rank_90 > 0.58**

| Metric | Value |
|--------|-------|
| Blocked | 32 trades |
| Remaining | 154 trades |
| Blocked losers / winners | 23 / 9 |
| Blocked mean return | -0.210% |
| Net PnL effect | **+$18,069** (HELPS) |

From D1.4 pre-registered candidate. Blocks 17% of trades for modest improvement.

### Rule 2: re2_breadth_share_gt_0.80
**Veto re-entry within 2 bars when breadth_ema21_share > 0.80**

| Metric | Value |
|--------|-------|
| Blocked | 15 trades |
| Remaining | 171 trades |
| Blocked losers / winners | 12 / 3 |
| Blocked mean return | -1.928% |
| Net PnL effect | **+$24,402** (HELPS) |

**Best rule.** Blocks fewest trades (15 = 8% of total) with best loser/winner ratio
(4:1). The 15 blocked trades span 2019-2025 (not concentrated). Of the 3 blocked
winners, one is large ($24K) — a single different trade could flip the sign.

### Rule 3: re6_funding_rank_gt_0.80
**Veto re-entry within 6 bars when funding_pct_rank > 0.80**

| Metric | Value |
|--------|-------|
| Blocked | 31 trades |
| Remaining | 134 trades (with funding data) |
| Blocked losers / winners | 19 / 12 |
| Blocked mean return | +1.404% |
| Net PnL effect | **-$43,854** (HURTS) |

**Hurts badly.** Despite the D1.3 funding signal, combining it with re-entry context
makes it worse — it blocks too many profitable re-entries during high-funding periods.

### Rule comparison

| Rule | Blocked | L/W Ratio | Net Effect | Verdict |
|------|---------|-----------|------------|---------|
| re6_breadth_rank | 32 (17%) | 2.6:1 | +$18K | Marginal |
| re2_breadth_high | 15 (8%) | 4.0:1 | +$24K | Best candidate |
| re6_funding_high | 31 (17%) | 1.6:1 | -$44K | REJECT |

## DIAGNOSTIC_DECISION

**WEAK** — The evidence shows:

1. **Re-entries are net profitable** (+$57K, 80 trades). A blanket cooldown would
   destroy positive PnL.

2. **No definition threshold separates re-entries significantly** (all MWU p > 0.79).
   The mean return gap is real in direction (94.4% bootstrap probability) but not
   significant at 95%.

3. **The PnL/trade gap is structural** — smaller winners from catching late-trend
   continuations, not identifiable bad states. This is a property of trend position,
   not a correctable error.

4. **One narrow conditional rule works**: re-entry within 2 bars when breadth > 0.80
   blocks 15 trades (12L/3W) for +$24K net. But:
   - 15 trades over 7 years (2.1/year)
   - One blocked winner ($24K) could flip the result
   - Not significant: can't test MWU on 15 vs 171

5. **Re-entries are integral to X0's advantage**: 27/29 X0-only trades (vs anchor)
   are re-entries contributing $43K. Aggressive re-entry filtering would erode the
   very advantage that robust ATR provides.

6. **No disproportionate pain**: re-entries are NOT overrepresented in worst trades.
   Worst re-entries are temporally dispersed, not concentrated in specific episodes.

## IF_PASS_SINGLE_BEST_CANDIDATE

IF a later diagnostic justifies implementing a conditional rule, the single best
candidate is:

- **Rule**: Veto re-entry within 2 bars when breadth_ema21_share > 0.80
- **Mechanism**: After X0 exit, if a new entry signal fires within 2 H4 bars
  AND breadth > 0.80, skip the entry
- **Historical effect**: blocks 15/186 trades (8%), 12L/3W, +$24K net PnL
- **Complexity**: trivial to implement (one condition on existing features)

This is pre-registered as a CONDITIONAL candidate. It must NOT be implemented
without further validation — the sample is too small (15 blocked trades) and
the result is sensitive to a single large blocked winner.

## RISKS_OF_FALSE_DISCOVERY

1. **Tiny sample for paper rules**: The best rule operates on 15 trades over 7 years.
   This is not a statistical basis for any rule — it's an observation.

2. **Winner sensitivity**: One blocked winner ($24K, trade 157) is 68% of the 3
   blocked winners' total PnL. If this trade had gone differently, the rule's
   net effect flips from +$24K to near zero.

3. **Multiple testing**: 3 rules tested × implicit search over breadth thresholds
   and BSE definitions. The "best" rule benefits from selection bias.

4. **Structural explanation for PnL/trade gap**: The gap comes from smaller winners
   (shorter continuations), not from identifiable bad states. A conditional rule
   addresses symptoms, not cause.

5. **Re-entries are positive-sum**: Total re-entry PnL is +$57K. Any filtering rule
   must clear a positive bar — it's removing from a profitable pool, not pruning losses.

6. **X0 advantage depends on re-entries**: 27/29 X0-only trades (vs anchor) are
   re-entries. Filtering re-entries works against the very mechanism that makes X0
   superior to E0_EMA21.

7. **Non-significance of core premise**: The re-entry vs non-re-entry return difference
   is not significant (MWU p=0.995). Without establishing that re-entries are
   systematically worse, conditional rules lack a theoretical foundation.
