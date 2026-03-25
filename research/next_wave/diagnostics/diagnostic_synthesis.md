# D1.6 — Diagnostic Synthesis and Next-Branch Decision

Date: 2026-03-07
Source: D1.3 (derivatives), D1.4 (breadth), D1.5 (re-entry) diagnostic reports

## BRANCH DECISION: D — No alpha overlay justified. Switch to execution engineering.

None of the three alpha overlay candidates (derivatives, breadth, conditional re-entry)
clears the evidence bar for implementation. The strongest individual result
(funding rate, Spearman r=-0.20) fails at the paper veto stage. The strongest
conditional result (re2_breadth_share > 0.80, +$24K on 15 trades) is too
small-sample to constitute evidence.

X0 should ship as-is. The next value comes from execution engineering (fill quality,
slippage measurement, order routing), not from adding alpha overlays.

---

## EVIDENCE_COMPARISON_MATRIX

| Dimension | A: Derivatives Veto | B: Breadth Veto | C: Re-entry-Lite |
|-----------|-------------------|-----------------|------------------|
| **Diagnostic decision** | WEAK | WEAK | WEAK |
| **Best p-value (full sample)** | 0.032 (funding MWU) | 0.390 (breadth MWU) | 0.995 (re vs nre MWU) |
| **Best Spearman r** | -0.197 (p=0.011) | -0.054 (p=0.460) | N/A |
| **Survives Bonferroni?** | No (adj p=0.096) | No (adj p=0.104) | N/A |
| **Signal present in full sample?** | Marginal | No | No |
| **Signal present in subset?** | Yes (non-re, p=0.009) | Yes (re-entry, p=0.026) | Yes (re2+breadth, 15 trades) |
| **Paper veto (full sample)** | ALL HURT or ~$0 | ALL HURT | N/A (no veto tested on full) |
| **Best paper veto (conditional)** | ~$0 (Q95, 9 trades) | +$18K (32 re-entries) | +$24K (15 trades) |
| **Quintile monotonicity** | Win rate: yes (weak) | Win rate: weak decrease | N/A |
| **Kruskal-Wallis p** | Not reported | 0.952 | N/A |

## DATA_QUALITY_COMPARISON

| Dimension | A: Derivatives | B: Breadth | C: Re-entry |
|-----------|---------------|------------|-------------|
| **Coverage of 186 entries** | 165 (88.7%) | 186 (100%) | 186 (100%) |
| **Data source** | Binance Futures API | bars_multi_4h.csv | X0 trade ledger |
| **Time range** | 2019-09 to 2026-02 | 2017-08 to 2026-02 | 2019-01 to 2026-02 |
| **Missing data** | 21 pre-Sept-2019 entries | None | None |
| **OI excluded** | Yes (83 records only) | N/A | N/A |
| **No-lookahead confidence** | HIGH (pointer alignment) | HIGH (bar-close alignment) | HIGH (by construction) |
| **Approximation risk** | None (exact funding times) | Moderate (H4 EMA(126) ≈ D1 EMA(21)) | None |
| **Confounding identified** | funding vs bse: r=-0.28 | breadth_pct_rank vs bse: r=0.39 | None internal |

## FALSE_DISCOVERY_RISK_COMPARISON

| Risk Factor | A: Derivatives | B: Breadth | C: Re-entry |
|-------------|---------------|------------|-------------|
| **Variables tested** | 3 (funding, pct_rank, basis) | 2 (share, pct_rank) | 3 rules |
| **Subsets tested** | 4 (re, non-re, post-stop, post-trend) | 4 (same) | Implicit (BSE × breadth) |
| **Effective tests** | ~12 | ~8 | ~6 |
| **Best raw p** | 0.011 | 0.026 | N/A (15-trade sample) |
| **Bonferroni-adj p** | ~0.13 | ~0.21 | N/A |
| **Sample size at decision** | 165 (full), 94 (subset) | 186 (full), 80 (subset) | 15 (rule operates on) |
| **Concentration risk** | Low (broad-based) | Moderate (Q2 trough drives signal) | High (1 winner flips result) |
| **Confounding severity** | Moderate (partial timing) | Substantial (r=0.39 with bse) | Low |
| **Theory-data alignment** | Partial (crowded→worse, but veto fails) | Reversed (worst in strong breadth) | Structural (smaller winners, not bad states) |

### Aggregate false discovery assessment

All three candidates suffer from the same core problem: the full-sample paper veto
— the only test that matters for implementation — either hurts or is near-zero for
every candidate. Positive results exist only in conditional subsets with small N
and non-surviving p-values.

The total effective test count across D1.3-D1.5 is ~26 (12 + 8 + 6). The best
raw p-value (0.011, funding pct_rank) has an experiment-wide adjusted p of ~0.29.
None of the findings would survive proper multiple-testing correction across the
full diagnostic program.

## IMPLEMENTATION_COMPLEXITY_COMPARISON

| Dimension | A: Derivatives | B: Breadth | C: Re-entry |
|-----------|---------------|------------|-------------|
| **New data dependency** | Binance Futures API (funding rate) | bars_multi_4h.csv (already available) | None (internal state only) |
| **Live data pipeline needed** | Yes (8h funding fetch) | Yes (13-alt H4 bar fetch) | No |
| **Feature computation** | Rolling pct_rank (90-event window) | EMA(126) per alt, fraction above | BSE counter + breadth check |
| **Strategy code change** | Add veto gate in entry logic | Add veto gate in entry logic | Add conditional in entry logic |
| **Parameters added** | 1 threshold | 1-2 thresholds | 2 (BSE, breadth) |
| **Testability** | Moderate (needs funding data in tests) | Moderate (needs breadth in tests) | Easy (internal state) |
| **Production risk** | Moderate (external API dependency) | Moderate (multi-asset data dependency) | Low |

All three are implementable with low complexity. This is not the differentiator.

## ECONOMIC_RATIONALE_COMPARISON

| Dimension | A: Derivatives | B: Breadth | C: Re-entry |
|-----------|---------------|------------|-------------|
| **Economic story** | Crowded funding → trend exhaustion → whipsaw | Broad market confirms vs denies BTC trend | Post-stop re-entries catch shorter continuations |
| **Story-data alignment** | Partial: signal exists but not actionable | Poor: worst trades in STRONG breadth | Good: structural explanation confirmed |
| **Falsifiability** | Medium: clear mechanism but veto fails | Low: data contradicts hypothesis direction | N/A: explains gap but doesn't fix it |
| **Expected going-forward value** | Low: 165 trades, p=0.032, veto hurts | Very low: p=0.39 full sample | Zero: gap is structural not fixable |

### The critical question

For each candidate: **Would you bet $1M of live capital that this overlay improves
risk-adjusted returns vs naked X0?**

- A (Derivatives): No. The signal is real but the paper veto — which simulates
  the actual impact of acting on it — shows zero or negative PnL improvement.
  A real signal that you can't profitably act on is worthless.

- B (Breadth): No. The full-sample signal doesn't exist (p=0.39). The conditional
  re-entry signal (p=0.026) is a subset phenomenon that doesn't survive Bonferroni.
  Worst trades concentrate in STRONG breadth, contradicting the overlay's rationale.

- C (Re-entry): No. Re-entries are net profitable (+$57K). The PnL/trade gap is
  structural (smaller winners from shorter continuations) — not a state you can
  filter. The best conditional rule operates on 15 trades where one blocked winner
  would flip the sign.

## BRANCH_DECISION

### **Branch D: No alpha overlay. Switch to execution engineering.**

## JUSTIFICATION_FOR_BRANCH_DECISION

### 1. The diagnostic program worked — it found the answer

The purpose of D1.3-D1.5 was to determine whether derivatives, breadth, or re-entry
signals justify an alpha overlay on X0. All three returned WEAK. This is not a
failure — it is the correct answer. X0's alpha comes from generic trend-following
with a robust trailing stop, and the diagnostics confirm that no overlay variable
meaningfully improves it.

### 2. Paper veto failure is decisive

The paper veto is the single most important test in the diagnostic suite. It
simulates the exact operation the overlay would perform (blocking entries in
specific states) and measures the net PnL impact. Every full-sample paper veto
across all three diagnostics either hurts or is near-zero. This is the canonical
evidence that implementation would destroy value, regardless of statistical
significance in outcome separation tests.

### 3. The alpha is not fragmented across states

If X0's alpha clustered in specific market states, overlays would be justified.
The diagnostics show the opposite:
- X0 is profitable across ALL breadth quintiles
- X0 is profitable across ALL funding quintiles (except Q4, barely negative)
- Re-entries are net profitable with similar win rates
- Worst trades do NOT cluster in identifiable contexts

This is a generic trend-following strategy. Its alpha is broad-based and
state-independent. Overlays would add complexity to a system that doesn't need it.

### 4. Conditional rules are too fragile

The strongest conditional results (breadth in re-entries, funding in non-re-entries)
are complementary — but complementarity of two WEAK signals does not produce a
STRONG composite. Each operates on ~80 trades with non-surviving p-values.
Implementing both would add 2-3 parameters for a combined paper effect of
roughly +$18K on 186 trades over 7 years — trivial relative to X0's $426K total PnL.

### 5. Execution engineering offers higher expected value

The next marginal dollar of improvement is more likely to come from:
- Measuring actual fill quality vs theoretical fills
- Optimizing order routing for BTC spot
- Reducing slippage through smarter execution timing
- Understanding bid-ask spread dynamics at X0's typical order sizes

These are measurable, non-overfittable, and directly improve the gap between
backtest and live performance — which is the binding constraint for a strategy
that already has strong alpha.

### 6. Pre-registered candidates remain available

If future data (more trades, more history) strengthens any of the conditional
signals, the pre-registered candidates can be re-evaluated without repeating
the diagnostic program:
- funding_pct_rank_30d (non-re-entry context)
- breadth_pct_rank_90 (re-entry context)
- re2_breadth_share > 0.80 (narrow conditional rule)

## NEXT_PROMPT_FAMILY_TO_RUN

### **E1.1 — Execution engineering: fill quality measurement**

The E-series focuses on reducing the gap between backtest assumptions and
live execution reality. E1.1 should:
- Characterize BTC/USDT H4-bar-open fill assumptions
- Measure bid-ask spread distribution at typical X0 entry/exit timestamps
- Estimate realistic slippage for X0's position sizes
- Compare cost scenario assumptions (smart/base/harsh) against available data

## TRACKS_TO_PARK_FOR_NOW

| Track | Status | Re-evaluation Trigger |
|-------|--------|----------------------|
| A: Derivatives overlay | PARKED | 200+ trades with OI data available |
| B: Breadth overlay | PARKED | Full-sample signal emerges (p < 0.01) |
| C: Conditional re-entry | PARKED | Re-entry vs non-re significant (p < 0.05) |
| Multi-signal composite (A+B) | PARKED | Either A or B reaches PASS individually |
| Basket/multi-coin portfolio | PARKED | Not until single-asset execution is proven |
| Event-gate / AI-parser | PARKED | Not until execution engineering complete |

### What would change this decision?

1. **More trades**: 186 is a small sample. At 300+ trades with derivatives coverage,
   the funding signal might survive Bonferroni. Re-evaluate after 2+ more years of live trading.

2. **OI data**: Open interest was excluded (83 records). If historical OI becomes
   available (exchange data backfill or alternative sources), it could add a
   dimension the current diagnostics couldn't test.

3. **Regime change**: If BTC enters a prolonged bear market where trend-following
   stops working, state-dependent overlays might become relevant. The current
   sample (2019-2026) covers only rising/choppy regimes.

4. **Live execution data**: If live fills show systematic slippage in specific
   market states (e.g., high funding = thin books), that would provide execution-level
   evidence for state-dependent order routing, distinct from alpha-level overlays.

---

## Summary of all diagnostics

| Diagnostic | Decision | Best Signal | Paper Veto (full) | Best Conditional | Verdict |
|-----------|----------|-------------|-------------------|------------------|---------|
| D1.3 Derivatives | WEAK | funding r=-0.20, p=0.011 | ALL HURT | ~$0 (Q95, 9 trades) | No overlay |
| D1.4 Breadth | WEAK | None (p=0.39) | ALL HURT | +$18K (re-entry, 32 trades) | No overlay |
| D1.5 Re-entry | WEAK | Structural gap, p=0.995 | N/A | +$24K (15 trades) | No overlay |
| **D1.6 Synthesis** | **Branch D** | — | — | — | **Execution engineering** |
