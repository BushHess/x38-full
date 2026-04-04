# Topic 019D1 — Pipeline Structure

**Topic ID**: X38-T-19D1
**Opened**: 2026-04-02
**Status**: OPEN
**Author**: human researcher
**Origin**: Split from Topic 019D (2026-04-02). Topic 019D had 4 findings
(DFL-08, DFL-10, DFL-11, DFL-12) covering pipeline structure, statistical
budget, and grammar expansion — three separable concerns. Split into 3
sub-topics for focused debate.
019D1 contains the 2 PIPELINE STRUCTURE findings: the 5-stage feature
graduation path and the Stage 2.5 data characterization proposal.

## Problem statement

These 2 findings define how discovered features move through the pipeline:

1. **DFL-08** (Feature Candidate Graduation Path): End-to-end 5-stage path
   from "pattern discovered in raw data" to "feature registered and validated."
   Connects DFL-06 analyses, DFL-02 reports, DFL-03 channels, and F-08 registry.

2. **DFL-10** (Pipeline Integration — Stage 2.5): Data characterization as a
   prerequisite stage between Stage 2 (Data audit) and Stage 3 (Feature scan).
   Profiles all data fields before grammar design.

## Scope

2 findings, 2 decisions (Tier 2):

| ID | Finding | Decision(s) |
|----|---------|-------------|
| DFL-08 | Feature candidate graduation path (5 stages) | D-05 (pre-filter top-N vs p-value, shared with DFL-11 in 019D2) |
| DFL-10 | Pipeline integration: Stage 2.5 data characterization | D-07 (new stage or expand Stage 2) |

This topic does NOT own:
- DFL-11: Statistical budget accounting (019D2)
- DFL-12: Grammar depth-2 composition (019D3)
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

- **Upstream (must close first)**: 019A (foundational boundaries — DFL-04/05/09 decisions constrain DFL-08 contamination rules), 019B (loop mechanisms — DFL-01/02/03 define analysis layer, reports, and channels that DFL-08 graduation path connects)
- **Upstream (CLOSED)**: 018 (bounded ideation, recognition stack), 002 (contamination firewall), 004 (meta-knowledge, MK-17 shadow-only)
- **Parallel**: 019D2 (statistical budget — D-05 pre-filter design is shared between DFL-08 and DFL-11)
- **Downstream**: feeds 003 (protocol engine — DFL-10 Stage 2.5 proposal affects pipeline design)

**Wave placement**: Wave 2.5C (after 019A foundational + 019B mechanisms).
Parallel with 019D2. All hard deps satisfied (018, 002, 004 CLOSED). Must
close BEFORE 003 — Stage 2.5 proposal affects protocol pipeline design.

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 003 | F-05 | Pipeline stages — **DFL-10 proposes Stage 2.5** between Stages 2-3 | 003 owns pipeline stage count. DFL-10 proposes; 003 decides |
| 006 | F-08 | Feature registry acceptance — DFL-08 Stage 4 + budget metadata | DFL-08 defines interface; DFL-11 (019D2) proposes budget_spent field; F-08 (006) defines registry schema |
| 015 | F-14 | DFL-10 proposes `data_profile.json` as new artifact | 015 owns artifact enumeration; DFL-10 proposes; 003 mediates |

## Files

| File | Purpose |
|------|---------|
| `findings-under-review.md` | 2 findings (DFL-08, DFL-10) + decision summary (2 decisions, Tier 2) |
| `final-resolution.md` | Created upon closure |
