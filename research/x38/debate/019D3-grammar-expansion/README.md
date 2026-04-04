# Topic 019D3 — Grammar Expansion

**Topic ID**: X38-T-19D3
**Opened**: 2026-04-02
**Status**: OPEN
**Author**: human researcher
**Origin**: Split from Topic 019D (2026-04-02). Topic 019D had 4 findings
(DFL-08, DFL-10, DFL-11, DFL-12) covering pipeline structure, statistical
budget, and grammar expansion — three separable concerns. Split into 3
sub-topics for focused debate.
019D3 contains 1 finding (DFL-12) — grammar depth-2 composition. Whether the
grammar should support composition operators creating ~140K features from
depth-1 OHLCV primitives, and the spirit-of-the-law question for SSE-D-02.

## Problem statement

This finding defines whether the grammar should EXPAND to support depth-2
composition — a qualitatively different kind of grammar extension that creates
features by combining existing features through operators:

1. **DFL-12** (Grammar Depth-2 Composition): Composition operators (ratio,
   diff, zscore, rank) creating ~140K features from depth-1 OHLCV primitives.
   ~460x expansion raises spirit-of-the-law question for SSE-D-02.

## Scope

1 finding, 1 decision (Tier 2):

| ID | Finding | Decision(s) |
|----|---------|-------------|
| DFL-12 | Grammar depth-2 composition (~140K expansion) | D-04 (should grammar support depth-2?) |

This topic does NOT own:
- DFL-08: Feature candidate graduation path (019D1)
- DFL-10: Pipeline integration — Stage 2.5 (019D1)
- DFL-11: Statistical budget accounting (019D2)
- Foundational boundary decisions (019A)
- Discovery loop mechanisms: AI analysis, reporting, feedback (019B)
- Raw data exploration scope (019C)
- Data foundation and quality assurance (019E)
- Data scope and profiling (019F)
- Pipeline stage design (003)
- Automated epistemic infrastructure (017)
- Bounded ideation rules (018, CLOSED)
- Contamination firewall content rules (002, CLOSED)

## Dependencies

- **Upstream (must close first)**: 019A (foundational boundaries — DFL-09 SSE-D-02 analysis/ideation distinction, DFL-12 spirit question depends on 019A outcome), 019D2 (statistical budget — budget capacity determines whether ~140K expansion is viable)
- **Upstream (CLOSED)**: 018 (bounded ideation, recognition stack), 002 (contamination firewall), 004 (meta-knowledge, MK-17 shadow-only)
- **Downstream**: feeds 003 (protocol engine — grammar expansion affects Stage 3 scan scope)

**Wave placement**: Wave 2.5D (AFTER 019D2 — budget outcome gates whether
~140K expansion is viable). All hard deps satisfied (018, 002, 004 CLOSED).
Must close BEFORE 003 — grammar expansion affects feature scan design.

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 018 | SSE-D-02 (rule 3, spirit) | Depth-2 composition within OHLCV — ~460x expansion violates spirit? | DFL-12 poses the question; debate decides |

## Files

| File | Purpose |
|------|---------|
| `findings-under-review.md` | 1 finding (DFL-12) + decision summary (1 decision, Tier 2) |
| `final-resolution.md` | Created upon closure |
