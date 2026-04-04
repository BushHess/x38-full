# Topic 019D2 — Statistical Budget

**Topic ID**: X38-T-19D2
**Opened**: 2026-04-02
**Status**: OPEN
**Author**: human researcher
**Origin**: Split from Topic 019D (2026-04-02). Topic 019D had 4 findings
(DFL-08, DFL-10, DFL-11, DFL-12) covering pipeline structure, statistical
budget, and grammar expansion — three separable concerns. Split into 3
sub-topics for focused debate.
019D2 contains 1 finding (DFL-11) — statistical budget accounting. Single
finding but ~250 lines with its own internal structure (budget model, two-tier
screening, lifecycle, accounting rules, 3 decisions).

## Problem statement

This finding defines the STATISTICAL CONSTRAINT on discovery — how finite
validation capacity limits how many features can be discovered and formally
tested from a finite dataset:

1. **DFL-11** (Statistical Budget Accounting): Explicit accounting for the
   finite validation capacity of the dataset. Two-tier screening (pre-filter
   vs formal test). The binding constraint on feature invention is statistical
   power, not search technology.

## Scope

1 finding, 3 decisions (Tier 3):

| ID | Finding | Decision(s) |
|----|---------|-------------|
| DFL-11 | Statistical budget accounting (two-tier screening) | D-09 (separate budget discovery vs grammar), D-10 (retroactive counting), D-11 (Tier 0 selection bias) |

This topic does NOT own:
- DFL-08: Feature candidate graduation path (019D1)
- DFL-10: Pipeline integration — Stage 2.5 (019D1)
- DFL-12: Grammar depth-2 composition (019D3)
- Foundational boundary decisions (019A)
- Discovery loop mechanisms: AI analysis, reporting, feedback (019B)
- Raw data exploration scope (019C)
- Data foundation and quality assurance (019E)
- Data scope and profiling (019F)
- Pipeline stage design (003)
- Grammar scan Holm correction (013)
- Automated epistemic infrastructure (017)
- Bounded ideation rules (018, CLOSED)
- Contamination firewall content rules (002, CLOSED)

## Dependencies

- **Upstream (must close first)**: 019A (foundational boundaries — DFL-09 scope classification determines what counts as "analysis" vs "ideation", which affects DFL-11 scope)
- **Upstream (CLOSED)**: 018 (bounded ideation, recognition stack), 002 (contamination firewall), 004 (meta-knowledge, MK-17 shadow-only)
- **Parallel**: 019D1 (pipeline structure — D-05 pre-filter design is shared between DFL-08 and DFL-11)
- **Downstream**: 019D3 (grammar expansion — D-09 budget outcome gates whether ~140K expansion is viable)

**Wave placement**: Wave 2.5C (after 019A foundational). Parallel with 019D1.
All hard deps satisfied (018, 002, 004 CLOSED). Must close BEFORE 019D3 —
budget capacity determines grammar expansion viability.

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 006 | F-08 | Feature registry — DFL-11 proposes budget_spent field in registry metadata | DFL-11 proposes; F-08 (006) defines registry schema |
| 013 | SSE-09 (Holm) | Grammar scan correction vs discovery loop budget — separate pools? | DFL-11 defines discovery-specific budget; 013 owns grammar-scan correction |

## Files

| File | Purpose |
|------|---------|
| `findings-under-review.md` | 1 finding (DFL-11) + decision summary (3 decisions, Tier 3) |
| `final-resolution.md` | Created upon closure |
