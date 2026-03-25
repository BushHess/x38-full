# D1.8 -- Final Branch Refresh After Integrity Reconciliation

Date: 2026-03-07
Source: D1.3, D1.4, D1.5, D1.6, D1.7 diagnostic and reconciliation reports

## BRANCH DECISION: D -- Execution engineering (CONFIRMED)

D1.7 integrity reconciliation resolved both outstanding concerns. The refreshed
evidence matrix, with exact D1 EMA(21) breadth and verified derivatives provenance,
produces the same branch decision as D1.6. No alpha overlay is justified.

---

## REFRESHED_EVIDENCE_MATRIX

| Dimension | A: Derivatives | B: Breadth | C: Re-entry-Lite |
|-----------|---------------|------------|------------------|
| **Diagnostic decision** | WEAK | WEAK | WEAK |
| **D1.7 integrity verdict** | VALID_WEAK (provenance proven) | CLEAN_WEAK (exact = proxy) | N/A (no integrity concern) |
| **Best p-value (full sample)** | 0.032 (funding MWU) | 0.344 (exact breadth MWU) | 0.995 (MWU) |
| **Survives Bonferroni (26 tests)?** | No (adj ~0.83) | No (adj ~8.9) | N/A |
| **Paper veto (full sample)** | ALL HURT | ALL HURT | N/A |
| **Best conditional effect** | ~$0 (Q95, 9 trades) | +$18K (32 re-entries) | +$24K→+$36K (15→22 trades) |
| **Conditional L/W ratio** | N/A | 2.6:1 | 4.0→2.7 under exact breadth |
| **Quintile monotonicity** | WR: weak decline | WR: weak decline, PnL: no | N/A |
| **Construction-sensitive?** | No (exact funding times) | Yes (7 trades change class) | Yes (via breadth dependency) |

### What D1.7 changed in the matrix

1. **Breadth MWU p moved from 0.390 to 0.344** -- slightly stronger but still non-significant.
   Direction: same (winners have lower breadth). Magnitude: trivial.

2. **Re-entry subset MWU p moved from 0.068 to 0.088** -- weaker under exact construction.
   The conditional breadth signal in re-entries DEGRADES with the correct metric.

3. **Paper rule re2_breadth>0.80: PnL improved (+$24K to +$36K) but L/W degraded
   (4.0 to 2.7) and blocked count increased (15 to 22)**. Seven trades changed
   classification between proxy and exact. This confirms threshold sensitivity --
   the rule is fragile to metric construction, which is the opposite of robustness.

4. **Derivatives provenance confirmed** -- funding data is real (Binance Futures API),
   7,067 records with authentic 8h intervals, no-lookahead alignment verified.
   The VALID_WEAK verdict means the data is genuine but the signal remains too weak.

## DATA_QUALITY_AND_VALIDITY_SUMMARY

| Data Source | Validity | Coverage | Integrity Concern | Resolution |
|-------------|----------|----------|-------------------|------------|
| Funding rates | PROVEN REAL | 165/186 (88.7%) | D1.1 said "none exists" | Fetched during D1.3 via API |
| Perp klines | PROVEN REAL | 165/186 (88.7%) | Same as above | Same resolution |
| OI | EXCLUDED | 83 records | Insufficient | Correctly excluded |
| Breadth (proxy) | VALID APPROX | 186/186 (100%) | H4 EMA(126) != D1 EMA(21) | r=0.86 entry-level |
| Breadth (exact) | PROVEN EXACT | 186/186 (100%) | N/A (this is the fix) | True D1 EMA(21) from resampling |
| Trade ledger | PROVEN EXACT | 186/186 (100%) | None | Actual BacktestEngine runs |

All data used in D1.3-D1.5 is genuine, correctly aligned (no lookahead), and
reproducible from archived scripts and artifacts.

## FALSE_DISCOVERY_RISK_SUMMARY

| Risk Factor | Pre-D1.7 | Post-D1.7 | Change |
|-------------|----------|-----------|--------|
| Total effective tests | ~26 | ~26 | Same |
| Best raw p | 0.011 (funding pct_rank) | 0.011 | Same |
| Experiment-wide adj p | ~0.29 | ~0.29 | Same |
| Breadth construction sensitivity | Unknown | 7/186 trades change class | NEW CONCERN |
| Re-entry conditional weakened? | No | Yes (0.068 -> 0.088) | Worse for C |
| Paper rule L/W degradation? | No | Yes (4.0 -> 2.7) | Worse for C |
| Derivatives provenance risk | Unknown | Zero (proven real) | Resolved |

**Net effect of D1.7 on false discovery risk: NEUTRAL to SLIGHTLY WORSE.**

The integrity reconciliation did not discover any hidden signal or improve any
existing one. The exact breadth construction slightly degrades the conditional
re-entry signal and makes the paper rule more threshold-sensitive. The derivatives
provenance concern is fully resolved but the signal was already too weak regardless.

## HARD_RULE_APPLICATION

### Rule 1: If derivatives provenance not proven -> A cannot be chosen

**RESULT: A IS NOT ELIMINATED BY PROVENANCE (provenance IS proven)**

D1.7 verified the full data chain: `fetch_derivatives_data.py` -> Binance Futures
REST API -> CSV artifacts -> pointer-based no-lookahead alignment -> entry features.
Data is authentic (8h intervals with <=50ms jitter, rate distribution matches known
BTC perp behavior). Spot-checked on trades 50 and 100.

**BUT A IS ELIMINATED BY SIGNAL WEAKNESS:**
- Full-sample paper veto: every threshold hurts (-$1.9K to -$131K)
- Funding p=0.032 does not survive Bonferroni across 26 tests (adj p ~0.83)
- Basis: no signal (MWU p=0.617)
- OI: excluded (83 records)

### Rule 2: If breadth remains weak after exact D1 EMA(21) -> B cannot be chosen

**RESULT: B IS ELIMINATED**

Under exact D1 EMA(21) construction:
- Full-sample MWU p=0.344 (was 0.390) -- still non-significant
- Full-sample Spearman r=-0.052 -- trivial
- All low-breadth vetoes HURT (-$18K to -$169K)
- Re-entry subset MWU p=0.088 (was 0.068) -- WEAKER than proxy
- Kruskal-Wallis: all quintiles positive, non-monotonic

The exact metric did not rescue the breadth signal. It slightly weakened the
only promising subset (re-entry). B cannot be chosen.

### Rule 3: If re-entry is fragile -> C cannot be chosen

**RESULT: C IS ELIMINATED**

The best conditional rule (re2_breadth>0.80) under exact breadth:
- Blocked trades: 22 (was 15) -- 7 trades changed classification
- L/W ratio: 2.7 (was 4.0) -- substantially degraded
- Net PnL: +$36K (was +$24K) -- improved, but this is incidental
- Still operates on 22 trades over 7 years (3.1/year)
- One blocked winner ($24K) can flip the result

The rule is MORE sensitive to metric construction than expected. A rule that
changes by 47% of its affected trades (7/15) when the underlying metric changes
from proxy to exact is not robust. C cannot be chosen.

### Rule 4: If none survives -> D

**RESULT: D CONFIRMED**

A eliminated by signal weakness (provenance proven but useless).
B eliminated by persistent non-significance under exact construction.
C eliminated by construction-sensitivity and small-sample fragility.

## BRANCH_DECISION

### Branch D: No alpha overlay. Switch to execution engineering.

This is the same decision as D1.6, now confirmed under stricter evidence.

## JUSTIFICATION_FOR_BRANCH_DECISION

### 1. D1.7 strengthened rather than weakened the D1.6 decision

The integrity reconciliation resolved both concerns in favor of existing conclusions:
- Derivatives data is real but the signal remains weak
- Exact breadth produces identical aggregate conclusions
- The best conditional rule DEGRADES under exact construction (L/W 4.0 -> 2.7)

If D1.7 had found that the proxy was badly distorting conclusions, it could have
reopened breadth. Instead, it confirmed proxy fidelity while revealing additional
fragility in the conditional rule.

### 2. Construction sensitivity is a new disqualifying factor

D1.7 revealed that 7/15 trades in the re2_breadth>0.80 rule change classification
between proxy and exact breadth (a 47% instability rate). For a rule operating on
15-22 trades, this level of sensitivity to metric construction method means:
- The rule is fitting to measurement noise, not to a real market state
- Any future metric refinement could flip the result
- This is a stronger argument against C than existed at D1.6

### 3. The paper veto test remains decisive

Across all reconciled evidence:
- Full-sample paper vetoes: ALL HURT (derivatives, breadth proxy, breadth exact)
- Conditional paper vetoes: marginal (+$18-36K on 15-32 trades)
- No threshold, metric construction, or subset produces a full-sample improvement

This is the canonical evidence that X0's alpha is state-independent.

### 4. Pre-registered candidates remain available

The reconciliation did not invalidate the pre-registered candidates. They are
frozen for re-evaluation when more data is available:
1. funding_pct_rank_30d (non-re-entry context)
2. breadth_pct_rank_90 (re-entry context, using exact D1 EMA(21))
3. re2_breadth_d1_exact > 0.80 (narrow conditional rule, exact metric)

## NEXT_PROMPT_FAMILY_TO_RUN

### E1.1 -- Execution engineering: fill quality measurement

Scope:
- Characterize BTC/USDT H4-bar-open fill assumptions vs real market microstructure
- Measure bid-ask spread distribution at typical X0 entry/exit timestamps
- Estimate realistic slippage for X0's position sizes
- Compare cost scenario assumptions (smart/base/harsh) against available data
- Quantify the backtest-to-live gap that execution engineering can close

This is the highest-value next step because:
1. X0's alpha is proven robust (186 trades, multiple cost scenarios, WFO, bootstrap)
2. The remaining uncertainty is in the execution gap, not in alpha discovery
3. Execution improvements are non-overfittable (they reduce costs, not add signals)
4. M15 data is available for microstructure analysis

## TRACKS_TO_PARK_FOR_NOW

| Track | Status | Re-evaluation Trigger | D1.7 Impact |
|-------|--------|----------------------|-------------|
| A: Derivatives overlay | PARKED | 200+ trades with OI data | Provenance proven; signal still weak |
| B: Breadth overlay | PARKED | Full-sample signal p < 0.01 | Exact metric confirms weakness |
| C: Conditional re-entry | PARKED | re vs nre p < 0.05 | L/W degrades under exact breadth |
| Multi-signal (A+B) | PARKED | Either A or B reaches PASS | Neither improved |
| Basket/multi-coin | PARKED | After execution engineering | No change |
| Event-gate/AI-parser | PARKED | After execution engineering | No change |

### What would change this decision?

Same triggers as D1.6, with one addition from D1.7:

1. **More trades** (300+ with derivatives coverage) could push funding past Bonferroni
2. **Historical OI** could add an untested dimension
3. **Regime change** (prolonged bear) could make state-dependent overlays relevant
4. **Live execution data** showing state-dependent slippage would motivate state-aware
   order routing (distinct from alpha overlays)
5. **NEW from D1.7**: If a future breadth metric construction (e.g., from a richer alt
   universe) produces stable trade classification (< 10% instability), the conditional
   re-entry rule could be re-examined

---

## Reconciliation Audit Trail

| Step | Date | Input | Output | Decision |
|------|------|-------|--------|----------|
| D1.3 | 2026-03-07 | Binance Futures API data | WEAK (funding r=-0.20, veto hurts) | No derivatives overlay |
| D1.4 | 2026-03-07 | D1.2 feature store (proxy breadth) | WEAK (p=0.39, re-entry p=0.026) | No breadth overlay |
| D1.5 | 2026-03-07 | D1.2 + D1.3 + D1.4 features | WEAK (structural gap, 15-trade rule) | No re-entry rule |
| D1.6 | 2026-03-07 | D1.3 + D1.4 + D1.5 | Branch D (execution engineering) | No overlay, switch tracks |
| D1.7 | 2026-03-07 | D1.3 scripts + exact breadth rebuild | VALID_WEAK + CLEAN_WEAK | Branch D confirmed |
| **D1.8** | **2026-03-07** | **D1.7 reconciled evidence** | **Hard rules applied** | **Branch D final** |
