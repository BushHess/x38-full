# Topic 019A — Discovery Foundations

**Topic ID**: X38-T-19A
**Opened**: 2026-04-02
**Status**: OPEN
**Author**: human researcher
**Origin**: Split from Topic 019 (2026-04-02). Topic 019 had 18 findings (3005
lines, 167KB) — too large for effective debate. Split into 9 sub-topics.
019A contains the 3 FOUNDATIONAL findings (Tier 1 decisions) that all other
sub-topics depend on. These must be debated FIRST.

## Problem statement

These 3 findings define the BOUNDARIES within which the discovery loop operates.
Every other 019 sub-topic (mechanisms, pipeline integration, budget, data
foundation) depends on how these boundaries are drawn:

1. **DFL-04** (Contamination Boundary): Is human-mediated feedback from the
   analysis layer "contamination laundering" or a fundamentally different
   information flow? This determines what the discovery loop is ALLOWED to do.

2. **DFL-05** (Deliberation-Gated Code Authoring): Is human-AI deliberation
   followed by gated code writing a SEPARATE mechanism from APE (SSE-D-11),
   or an exception to the "no code generation" rule? This determines HOW the
   discovery loop produces running code.

3. **DFL-09** (SSE-D-02 Scope Clarification): Is DFL-06/07 analysis a DIFFERENT
   activity from SSE-D-02 bounded ideation? This determines WHAT DATA the
   discovery loop can observe (OHLCV-only vs all 13 fields).

Until these 3 decisions are made, downstream sub-topics cannot resolve their
own questions — they all assume specific answers to D-01, D-02, D-03.

## Scope

3 findings, 3 Tier 1 decisions:

| ID | Finding | Decision |
|----|---------|----------|
| DFL-04 | Contamination boundary for the discovery loop | D-02: Different or Same? |
| DFL-05 | Deliberation-gated code authoring | D-03: Separate or Exception? |
| DFL-09 | SSE-D-02 scope clarification for systematic scan | D-01: YES or NO? |

This topic does NOT own:
- Discovery loop mechanisms (019B)
- Raw data exploration scope (019C)
- Pipeline integration and budget (019D)
- Data foundation and quality assurance (019E)
- Grammar composition (019F)
- Pipeline stage design (003)
- Automated epistemic infrastructure (017)
- Bounded ideation rules (018, CLOSED)
- Contamination firewall content rules (002, CLOSED)

## Dependencies

- **Upstream (CLOSED)**: 018 (bounded ideation, recognition stack), 002 (contamination firewall), 004 (meta-knowledge, MK-17 shadow-only)
- **Downstream**: 019B, 019C, 019D, 019E, 019F (all depend on 019A outcomes)

**Wave placement**: Wave 2.5A (debate FIRST among 019 sub-topics). All hard
deps satisfied (018, 002, 004 CLOSED). Must close BEFORE any other 019
sub-topic — foundational decisions constrain all downstream debate.

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 018 | SSE-D-02 (rule 1) | Bounded ideation results-blind vs discovery loop results-aware | DFL-04 defines contamination boundary |
| 018 | SSE-D-02 (rule 3) | OHLCV-only rule vs DFL-06 scan using all 13 fields — analysis != ideation | DFL-09 proposes scope clarification: SSE-D-02 applies to automated ideation only |
| 018 | SSE-D-11 | APE v1 no code gen. DFL-05 proposes deliberation-gated code authoring as SEPARATE mechanism | DFL-05 defines scope boundary: automated gen (SSE-D-11) vs deliberation-gated authoring (DFL-05) |
| 002 | F-04 | Firewall typed schema — analysis outputs need classification | DFL-04 classifies all analysis outputs as process observations |

## Files

| File | Purpose |
|------|---------|
| `findings-under-review.md` | 3 findings (DFL-04, DFL-05, DFL-09) + decision summary (3 Tier 1 decisions) |
| `final-resolution.md` | Created upon closure |
