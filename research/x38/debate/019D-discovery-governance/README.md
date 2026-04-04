# Topic 019D — Discovery Governance

**Topic ID**: X38-T-19D
**Opened**: 2026-04-02
**Status**: SPLIT (2026-04-02)
**Author**: human researcher
**Origin**: Split from Topic 019 (2026-04-02). Topic 019 had 18 findings (3005
lines, 167KB) — too large for effective debate. Split into 9 sub-topics.
019D contained the 4 GOVERNANCE findings about how discovery integrates with
the framework: graduation path, pipeline stage, statistical budget, grammar
composition.

> **NOTE**: Topic 019D has been split into 3 sub-topics (2026-04-02). This file
> retains the finding index pointing to the new topics. Original
> `findings-under-review.md` (754 lines) is kept as archived reference.
>
> **Reason for split**: 4 findings with 3 separable concerns (pipeline structure,
> statistical budget, grammar expansion) and different dependency chains.
> 019D3 depends on 019D2 budget outcome — sequential within 019D, but 019D1
> and 019D2 can debate in parallel.

## Split Structure

### Wave 2.5C — Parallel

| Sub-topic | Slug | Findings | Decisions | Dep |
|-----------|------|----------|-----------|-----|
| **019D1** | pipeline-structure | DFL-08, DFL-10 | D-05, D-07 (Tier 2) | 019A, 019B |
| **019D2** | statistical-budget | DFL-11 | D-09, D-10, D-11 (Tier 3) | 019A |

### Wave 2.5D — After 019D2

| Sub-topic | Slug | Findings | Decisions | Dep |
|-----------|------|----------|-----------|-----|
| **019D3** | grammar-expansion | DFL-12 | D-04 (Tier 2) | 019A, 019D2 |

## Debate Wave Diagram

```
Wave 2.5C:  019D1 (Pipeline Structure)  ───  019D2 (Statistical Budget)
                                                    │
Wave 2.5D:                                    019D3 (Grammar Expansion)
```

## Finding Index — Pointing to new sub-topics

| Issue ID | Finding | Sub-topic | Classification | Status |
|----------|---------|-----------|---------------|--------|
| X38-DFL-08 | Feature candidate graduation path (5 stages) | **019D1** | Thiếu sót | Open |
| X38-DFL-10 | Pipeline integration: Stage 2.5 data characterization | **019D1** | Thiếu sót | Open |
| X38-DFL-11 | Statistical budget accounting (two-tier screening) | **019D2** | Thiếu sót | Open |
| X38-DFL-12 | Grammar depth-2 composition (search space expansion) | **019D3** | Thiếu sót | Open |

## Files

| File | Purpose |
|------|---------|
| `findings-under-review.md` | **ARCHIVED** — original 4 findings (754 lines). Kept as reference only. |
| Sub-topic directories | Active debate locations (see split structure above) |
