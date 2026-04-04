# Topic 019F — Regime Dynamics

**Topic ID**: X38-T-19F
**Opened**: 2026-04-02
**Status**: OPEN
**Author**: human researcher
**Origin**: Split from Topic 019 (2026-04-02). Regrouped 2026-04-02 to fix
DFL-14/DFL-18 cross-boundary tension. DFL-14 moved here from 019E; DFL-18
kept here; DFL-15 and DFL-16 moved to 019G (Data Scope). 019F now contains
2 REGIME DYNAMICS findings that have a documented conflict requiring joint
resolution.

Theme: "How does data change over time? Are features stable across regimes?"

## Problem statement

These 2 findings address how data CHANGES OVER TIME and whether discovered
features are STABLE across different market conditions:

1. **DFL-14** (Non-Stationarity Protocol): When DGP structural breaks are
   detected, what does the framework DO? Detection tools exist (DFL-06/07),
   but no response protocol: how to classify features by prospective validity,
   how to distinguish signal decay from DGP change from regime shift. Uses
   DGP-detected regimes (PELT/CUSUM).

2. **DFL-18** (Regime-Conditional Profiling): A systematic protocol for testing
   every discovered feature across every identified regime, producing a
   feature x regime interaction matrix with stability scores. Uses hand-defined
   market regimes (bull/bear/range/vol quartiles).

**KEY**: These two findings have a documented TENSION — DFL-14's DGP-detected
regimes and DFL-18's hand-defined regimes can produce conflicting feature
classifications. By placing them in the same topic, debaters can resolve
the conflict directly (precedence rules, integration strategy, or regime
source unification).

Both are Tier 4 decisions — independent of Tier 1-3 (discovery loop
architecture, mechanisms, budget). They can be debated in PARALLEL with all
other 019 sub-topics.

## Scope

2 findings, 2 decisions (Tier 4, independent), plus DFL-14/DFL-18 tension
resolution:

| ID | Finding | Decision(s) |
|----|---------|-------------|
| DFL-14 | Non-stationarity protocol — DGP change detection & feature shelf-life | D-17: Shelf-life classification mandatory? |
| DFL-18 | Systematic feature regime-conditional profiling | D-21: Regime profiling mandatory? |

Additional resolution: DFL-14/DFL-18 regime conflict (precedence, integration,
or unification of regime sources).

This topic does NOT own:
- Discovery loop architecture (019A)
- AI analysis and reporting (019B)
- Systematic data exploration (019C)
- Discovery governance and budget (019D)
- Data pipeline quality: trustworthiness, synthetic validation (019E)
- Data scope: resolution gaps, cross-asset context (019G)
- Pipeline stage design (003)
- Automated epistemic infrastructure (017)
- Bounded ideation rules (018, CLOSED)
- Contamination firewall content rules (002, CLOSED)

## Dependencies

- **Upstream (CLOSED)**: 018 (bounded ideation, recognition stack), 002 (contamination firewall), 004 (meta-knowledge, MK-17 shadow-only)
- **NONE from other 019 sub-topics**. Independent cluster — does not depend on 019A outcomes.
- **Informational**: 019E (DFL-13 volume trustworthiness affects both DFL-14 and DFL-18 regime definitions, but does not block debate)

**Wave placement**: Wave 2.5 parallel (can debate simultaneously with 019A and
all other 019 sub-topics). All hard deps satisfied (018, 002, 004 CLOSED).
Tier 4 decisions are independent of Tier 1-3 foundational decisions.

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 013 | SSE-04 (convergence thresholds) | DGP breaks across campaigns — DFL-14 shelf-life classification | DFL-14 regime/epoch classification feeds into 013's convergence framework (equivalence thresholds may need DGP-conditioning) |
| 019E | DFL-13 (data trustworthiness) | Volume reliability affects both DFL-14 Layer 2 detection and DFL-18 volume regimes | If DFL-13 finds volume unreliable, both regime methods are compromised. 019E validation should precede or run in parallel |
| 019G | DFL-15 (data scope) | DFL-14 Layer 2 detection quality depends on available data resolution | Higher-resolution data (019G scope decision) improves DGP detection power |

## DFL-14/DFL-18 conflict — pre-debate resolution strategy

**Purpose**: This is the primary reason DFL-14 and DFL-18 were grouped into a
single topic. The conflict is NOT a secondary issue — it is the CENTRAL question.
Debaters must resolve it BEFORE D-17 and D-21 can be finalized, because the
regime conflict directly affects whether each finding is mandatory/advisory.

### The conflict in one sentence

DFL-14 detects regimes from DATA (PELT/CUSUM → structural breaks), DFL-18
defines regimes from THEORY (bull/bear/range/vol quartiles). Both produce regime
labels, but the labels can DISAGREE on which regime a feature belongs to.

### Resolution options (exhaustive — debaters pick one)

**Option 1: CONDITION hand-defined regimes by DGP boundaries**
- Use DFL-14 Layer 2's DGP-detected BOUNDARIES to SEGMENT the data, then
  apply DFL-18's hand-defined regimes (bull/bear/range/vol) WITHIN each segment.
  Stability score computed per (DGP segment × market regime) cell.
- **CRITICAL DISTINCTION**: DFL-14 detects CHANGE POINTS (discrete structural
  events — FTX collapse, ETF approval). DFL-18 defines MARKET STATES (cyclical
  patterns — bull/bear/range). These are orthogonal concepts. Do NOT conflate
  breaks with regimes. This option COMBINES them, not replaces one with the other.
- Pro: Accounts for DGP changes without losing market-regime vocabulary.
  A feature classified as REGIME-INVARIANT in pre-FTX data may be EPOCH-SPECIFIC
  in post-FTX data — this distinction is only visible with conditioning.
- Con: Adds dimensionality (DGP segment × market regime × volume regime).
  Sparse cells likely with 188 current-strategy trades (though future features
  are tested on full historical dataset, not just current strategy trades).
- **Key test**: How many DGP segments does Layer 2 detect on BTC 2017-2026?
  If 3-5, conditioning is tractable. If 15+, cells become too sparse.

**Option 2: PRECEDENCE rule**
- Run BOTH DFL-14 and DFL-18 independently. When they conflict, a fixed
  precedence rule determines the final classification.
- Sub-options:
  - DFL-14 wins (data-driven > theory-driven)
  - DFL-18 wins (strategy-aligned > statistically detected)
  - Most restrictive wins (e.g., if either says REGIME-DEPENDENT, it is)
- Pro: Preserves both perspectives. More information retained.
- Con: Adds complexity. Two passes at DFL-08 Stage 2. Precedence rule may feel
  arbitrary.

**Option 3: DUAL metadata, human resolves**
- Both DFL-14 and DFL-18 produce independent classifications. Both are recorded
  as metadata in the feature registry. Human researcher (Tier 3 authority)
  resolves conflicts per feature.
- Pro: Maximum information. Aligned with 3-tier authority model (machine
  provides evidence, human decides).
- Con: Does not scale. Defeats the purpose of a systematic protocol. Every
  conflicting feature becomes a judgment call.

### Recommended debate ordering

```
Step 1: UNIFICATION question — can DFL-14's DGP regimes replace DFL-18's
        hand-defined regimes? (This is the highest-leverage question.)
  ├── YES → DFL-18 adopts DFL-14 regimes. Conflict eliminated.
  │         D-17 and D-21 can merge into a single "regime assessment" decision.
  └── NO → Step 2
              ↓
Step 2: PRECEDENCE or DUAL? Pick one.
  ├── PRECEDENCE → define which system wins and why.
  └── DUAL → accept two metadata fields, document when human resolves.
              ↓
Step 3: D-17 (shelf-life mandatory?) and D-21 (profiling mandatory?) —
        now resolvable given the regime source decision.
```

**Step 1 is the critical question.** If debaters spend rounds on D-17 and D-21
without resolving the regime source first, those decisions may need to be
revisited after the conflict is settled.

### Upstream dependency

**CRITICAL**: Volume-based regime methods in both DFL-14 (Layer 2) and DFL-18
(Type 2 volume regimes) depend on Topic 019E (DFL-13) validating volume data
trustworthiness. If 019E concludes volume is Category A (unreliable), volume-based
regime definitions are compromised. 019E can run in parallel but its conclusions
may require revisiting this topic's resolution.

### Evidence to inform the choice

- **E5-ema21D1 regime filter**: Uses hand-defined D1 EMA(21) regime (bull/bear).
  Successful production example of hand-defined regimes. Argues for keeping
  DFL-18's vocabulary.
- **X27 EDA** [extra-archive]: Found volume non-stationarity with structural breaks
  (rolling 30-day volume peaked ~24K BTC/bar 2022, dropped to ~3.5K by 2025).
  This is a DGP-level change, not a market regime cycle. Argues for DFL-14's
  data-driven detection. (Source: `research/x27/REPORT.md` volume analysis section.)
- **Trade count constraint**: Current E5-ema21D1 has 188 trades, but DFL-14/DFL-18
  apply to FUTURE discovered features tested on the full historical dataset
  (2017-2026, ~25K H4 bars), not just the current strategy's trade count. Cell
  sparsity is a concern for current-strategy validation, but less so for raw
  feature IC computation across millions of data points.

## Debate plan

- Estimated: 2-3 rounds (regime conflict FIRST, then D-17 and D-21)
- Key battles:
  - **Round 1**: DFL-14/DFL-18 regime conflict resolution (Step 1: unify or not?)
  - **Round 2**: D-17 and D-21 (shelf-life + profiling mandatory/advisory),
    informed by Round 1 outcome
  - **Round 3 (if needed)**: Integration details, WFO redundancy argument
- Fallback: if regime conflict not resolved in Round 1, escalate to Judgment
  call with explicit tradeoff documentation per rules.md §14.

## Files

| File | Purpose |
|------|---------|
| `findings-under-review.md` | 2 findings (DFL-14, DFL-18) + DFL-14/DFL-18 tension analysis + decision summary (2 Tier 4 decisions) |
| `final-resolution.md` | Created upon closure |
