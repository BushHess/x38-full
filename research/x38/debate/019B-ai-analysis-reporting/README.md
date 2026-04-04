# Topic 019B — AI Analysis & Reporting

**Topic ID**: X38-T-19B
**Opened**: 2026-04-02
**Status**: OPEN
**Author**: human researcher
**Origin**: Split from Topic 019 (2026-04-02). Topic 019 had 18 findings and was
too large for effective debate. 019B contains the 3 core loop findings that define
how AI observes, reports, and incorporates human feedback.

## Scope

3 findings (DFL-01, DFL-02, DFL-03), 4 Tier 2 decisions.

This topic owns the **core observation-reporting-feedback loop**:

1. **DFL-01**: AI result analysis & pattern surfacing — what the analysis layer
   observes (results AND raw data) and how it surfaces patterns
2. **DFL-02**: Human-facing report contract — how findings are structured for
   human consumption (DiscoveryReport schema)
3. **DFL-03**: Human feedback capture & grammar evolution — how human intuitions
   become search directions (3 feedback channels)

This topic does NOT own:
- Discovery foundations: contamination boundary (DFL-04), code authoring (DFL-05),
  SSE-D-02 scope clarification (DFL-09) — owned by 019A
- Systematic data exploration: DFL-06, DFL-07 — owned by 019C
- Discovery governance: DFL-08, DFL-10, DFL-11, DFL-12 — owned by 019D
- Data foundation & quality assurance: DFL-13 to DFL-18 — owned by 019E/019F

## Decisions this topic must resolve

| ID | Decision | Finding | Alternatives |
|----|----------|---------|-------------|
| D-06 | Is the human SSE-D-02 exception for templates correct? | DFL-03 | YES (provenance-tracked) / NO (results-blind required for ALL sources) |
| D-08 | AI analysis layer: automatic or on-demand? | DFL-01 | Automatic (post-validation) / On-demand (human request) / Both |
| D-13 | AI analysis layer: stateless or stateful (memory across reports)? | DFL-01 | Stateless / Stateful (contamination risk per DFL-04) |
| D-14 | Findings cap per report? | DFL-02 | Fixed N=10 / Dynamic by confidence / Uncapped |

All 4 decisions are Tier 2 (mechanisms). They depend on 019A resolving D-01, D-02,
D-03 first (foundational boundary decisions).

## Dependencies

- **Upstream (must resolve first)**:
  - 019A (discovery foundations) — D-01 (analysis vs ideation boundary), D-02
    (human-mediated feedback contamination status), D-03 (code authoring scope).
    019B's decisions require these foundational answers.
  - 018 (CLOSED) — SSE-D-02 (bounded ideation), SSE-D-11 (APE v1)
  - 002 (CLOSED) — F-04 (contamination firewall)
  - 004 (CLOSED) — MK-17 (shadow-only)
- **Parallel**: 019C (systematic data exploration) — independent scope, no blocking deps
- **Downstream**: 019D (discovery governance) — governance mechanisms depend on
  what 019B defines for the core loop

## Wave assignment

**Wave 2.5B**: After 019A, parallel with 019C. Must close before 019D (governance
needs to know the core loop shape) and before 003 (protocol engine may need
AI analysis hooks).

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 017 | ESP-01 | epistemic_delta.json vs DiscoveryReport — complementary scope | DFL-02 defines complementary (not competing) reporting |
| 017 | ESP-04 | Budget governor vs human "investigate this" directives | DFL-03 feedback = input to human decisions, not budget override |
| 018 | SSE-D-02 (rule 1) | Bounded ideation results-blind vs discovery loop results-aware | DFL-03 proposes deliberate exception for human templates (D-06) |

## Debate plan

- Estimated: 1-2 rounds (scope is tight: 3 findings, 4 decisions)
- Key battles:
  - D-06: SSE-D-02 exception for human templates — contamination backdoor or
    necessary pragmatism? Burden on proposer (DFL-03).
  - D-08 + D-13: Automatic vs on-demand and stateless vs stateful are linked —
    automatic + stateful maximizes coverage but maximizes contamination risk.
  - D-14: Findings cap interacts with D-08 trigger mode (automatic generates
    more reports, cap becomes more important).
- Prerequisite check: 019A D-01, D-02, D-03 must be resolved before debate starts.

## Files

| File | Purpose |
|------|---------|
| `findings-under-review.md` | 3 findings (DFL-01, DFL-02, DFL-03) + 4 decisions + summary table |
| `final-resolution.md` | Created upon closure |
