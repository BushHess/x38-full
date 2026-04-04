# Topic 019C — Systematic Data Exploration

**Topic ID**: X38-T-19C
**Opened**: 2026-04-02
**Status**: OPEN
**Author**: human researcher
**Origin**: Split from Topic 019 (2026-04-02). Topic 019 had 18 findings (3005
lines, 167KB) — too large for effective debate. Split into 9 sub-topics.
019C contains the data exploration catalog (DFL-06, 10 analyses) and methodology
toolkit (DFL-07, 6 method categories A-F). These two findings are tightly coupled
and cannot be separated — the catalog defines WHAT to analyze, the methodology
defines HOW.

**Note**: This is the LARGEST sub-topic (~870 lines of findings) but the two
findings are inseparable. DFL-06's 10 analyses require DFL-07's methodology to
be actionable; DFL-07's methods are meaningless without DFL-06's analysis targets.

## Problem statement

The framework has no mechanism for systematic exploration of raw market data.
Topic 006 enumerates features humans already designed. DFL-01 (019B) analyzes
results humans already produced. But 8 of 13 data fields have never been used
in any indicator, 6 derivable features have never been computed, and multiple
analytical dimensions (intrabar patterns, lead-lag across timeframes, event-based
dynamics) have never been explored despite data being available since 2017.

DFL-06 catalogs 10 concrete analyses covering these gaps. DFL-07 provides the
statistical methods, visualization techniques, and discovery workflow that make
raw data analysis systematic and reproducible rather than ad-hoc.

The debate question is narrow: **D-12 — should the 10 analyses and methodology
be part of the framework SPEC (defining the method space) or deferred to the
first campaign's methodology?**

## Scope

2 findings, 1 Tier 3 decision:

| ID | Finding | Decision |
|----|---------|----------|
| DFL-06 | Systematic raw data exploration — untapped fields & patterns (10 analyses) | D-12: Architecture (method space) / Research plan (defer) / Split |
| DFL-07 | Raw data analysis methodology & techniques (6 categories A-F) | D-12: Architecture (method space) / Research plan (defer) / Split |

This topic does NOT own:
- Discovery loop foundations (019A)
- AI analysis layer and reporting (019B)
- Pipeline integration, budget, grammar composition (019D)
- Data foundation and quality assurance (019E)
- Data scope and profiling (019F)
- Pipeline stage design (003)
- Automated epistemic infrastructure (017)
- Bounded ideation rules (018, CLOSED)
- Contamination firewall content rules (002, CLOSED)

## Dependencies

- **Upstream (CLOSED)**: 018 (bounded ideation, recognition stack), 002 (contamination firewall), 004 (meta-knowledge, MK-17 shadow-only)
- **Upstream (must close first)**: 019A — foundational decisions including DFL-09 scope (D-01: is analysis exempt from OHLCV-only?). DFL-06 scans all 13 fields; if D-01 = NO, scope changes
- **Parallel**: 019B (AI analysis layer — DFL-07 provides the methodology toolkit that DFL-01's analysis layer would use)

**Wave placement**: Wave 2.5B (after 019A, parallel with 019B). Depends on 019A
closing (including D-01 SSE-D-02 scope resolution), which determines whether DFL-06 can use
non-OHLCV fields. Must close BEFORE 003 — analyses may introduce protocol
interactions.

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 018 | SSE-D-02 (rule 3) | OHLCV-only rule vs DFL-06 scan using all 13 fields | Resolved by DFL-09 (019A) but needs debate confirmation |
| 018 | SSE-D-02 (rule 3, spirit) | Depth-2 composition within OHLCV — violates spirit? | DFL-12 (019D) poses question |

## Debate scope clarification — managing 862-line findings

**Context load warning**: The findings file is 862 lines — the largest of any
sub-topic. However, the debate question is NARROW (a single D-12 decision).
The 10 analyses and 6 methodology categories are EVIDENCE for the meta-decision,
NOT individual debate items.

**Debaters should**:
1. Focus on D-12: should the 10 analyses + methodology be architecture spec
   (defining method space) or deferred to the first campaign's methodology?
2. Treat individual analyses (1-10) and methods (A-F) as EXAMPLES demonstrating
   scope and feasibility — not as items requiring individual accept/reject decisions.
3. DO debate whether the analyses are **technically sound** enough to be
   architecture spec (methodology correctness, questions well-formed). Do NOT
   debate whether to **prioritize** specific analyses within the method space —
   that's a campaign-level decision, not architecture.

**The key debate tension is**:
- **PRO architecture**: Defining the method space in the spec ensures consistency
  across campaigns. Without it, each campaign reinvents the wheel.
- **PRO defer**: The method space is too detailed for a framework spec. Methods
  evolve faster than architecture. Locking them in creates rigidity.
- **SPLIT option**: Architecture owns the OBLIGATION to do systematic data
  exploration (with quality criteria). Campaign owns WHICH analyses and methods.

**If debaters find the 862 lines overwhelming**: request decision_owner (human
researcher) to provide a condensed summary that preserves technical evidence
(1-2 pages per finding). Per rules.md §10 ("Nếu đáng nêu ra, đáng tranh luận
đúng cách"), do not skip details entirely — instead, agree at Round 1 start
on a reading strategy. Recommended minimum:
- DFL-06: first paragraph + "What" line + "Prior evidence" per analysis
- DFL-07: category headers + "Key value" statement per method
- Cross-topic tensions and Open questions in full

**CRITICAL**: If either debater challenges the technical soundness of any
analysis or method, the full details for that item MUST be read. Skipping
is not equivalent to pre-accepting quality.

## Files

| File | Purpose |
|------|---------|
| `findings-under-review.md` | 2 findings (DFL-06, DFL-07) + decision summary (D-12) |
| `final-resolution.md` | Created upon closure |
