# Topic 019 — Discovery Feedback Loop

**Topic ID**: X38-T-19
**Opened**: 2026-03-29
**Status**: SPLIT (2026-04-02)
**Author**: human researcher
**Origin**: Gap identified during Topic 018 closure audit — 018 designed discovery
infrastructure (bounded ideation, recognition stack, APE) but missed the mechanism
by which interesting findings are actually discovered. 100% of project alpha
(VDO, EMA(21d) regime, E5) came from human intuition informed by data analysis,
not from grammar enumeration or template parameterization.

> **NOTE**: Topic 019 đã được chia thành 9 sub-topics (2026-04-02). File này
> chỉ còn giữ lại finding index trỏ tới topic mới. Original `findings-under-review.md`
> (3005 lines, 167KB) được giữ nguyên làm reference.
>
> **Lý do chia tách**: 18 findings / 22 decisions / 167KB trong một topic duy nhất
> không thể debate hiệu quả. Chia thành 9 sub-topics cho phép:
> - Debate song song (019E + 019F song song với tất cả)
> - Context nhỏ hơn cho mỗi debate (~250-870 lines thay vì 3005)
> - Dependency ordering rõ ràng (019A trước, 019B/C song song, 019D sau)

## Split Structure

### Wave 2.5A — Debate FIRST (foundations)

| Sub-topic | Slug | Findings | Decisions | Lines |
|-----------|------|----------|-----------|-------|
| **019A** | discovery-foundations | DFL-04, DFL-05, DFL-09 | D-01, D-02, D-03 (Tier 1) | ~354 |

### Wave 2.5B — After 019A (parallel)

| Sub-topic | Slug | Findings | Decisions | Lines |
|-----------|------|----------|-----------|-------|
| **019B** | ai-analysis-reporting | DFL-01, DFL-02, DFL-03 | D-06, D-08, D-13, D-14 (Tier 2) | ~252 |
| **019C** | systematic-data-exploration | DFL-06, DFL-07 | D-12 (Tier 3) | ~862 |

### Wave 2.5C — After 019A+B (019D SPLIT into 019D1/D2/D3)

| Sub-topic | Slug | Findings | Decisions | Lines |
|-----------|------|----------|-----------|-------|
| ~~**019D**~~ | ~~discovery-governance~~ | ~~DFL-08, DFL-10, DFL-11, DFL-12~~ | ~~D-04, D-05, D-07, D-09, D-10, D-11~~ | ~~753~~ |
| **019D1** | pipeline-structure | DFL-08, DFL-10 | D-05, D-07 (Tier 2) | ~365 |
| **019D2** | statistical-budget | DFL-11 | D-09, D-10, D-11 (Tier 3) | ~252 |
| **019D3** | grammar-expansion | DFL-12 | D-04 (Tier 2) | ~138 |

### Wave 2.5 parallel — Independent (debate anytime, regrouped 2026-04-02)

| Sub-topic | Slug | Findings | Decisions | Lines |
|-----------|------|----------|-----------|-------|
| **019E** | data-quality-validation | DFL-13, DFL-17 | D-15, D-16, D-20, D-22 (Tier 4) | ~320 |
| **019F** | regime-dynamics | DFL-14, DFL-18 | D-17, D-21 (Tier 4) + tension resolution | ~365 |
| **019G** | data-scope | DFL-15, DFL-16 | D-18, D-19 (Tier 4) | ~240 |

> **Regroup (2026-04-02)**: DFL-14 moved 019E→019F, DFL-15+16 moved 019F→019G.
> Lý do: DFL-14↔DFL-18 có tension (conflicting regime classifications) cần debate cùng nhau.

## Debate Wave Diagram

```
Wave 2.5A:  019A (Foundations)         ─── 019E (Data Quality Validation, independent)
                │                       ─── 019F (Regime Dynamics, independent)
Wave 2.5B:  019B (Core Loop)  ───  019C (Data Exploration)  ─── 019G (Data Scope, independent)
                │
Wave 2.5C:  019D1 (Pipeline)  ───  019D2 (Budget)
                                        │
Wave 2.5D:                        019D3 (Grammar)
```

Estimated total: 5-6 rounds (vs 12-15 sequential with original single topic).

## Finding Index — Trỏ tới sub-topic mới

| Issue ID | Finding | Sub-topic | Classification | Status |
|----------|---------|-----------|---------------|--------|
| X38-DFL-01 | AI result analysis & pattern surfacing | **019B** | Thiếu sót | Open |
| X38-DFL-02 | Human-facing report contract | **019B** | Thiếu sót | Open |
| X38-DFL-03 | Human feedback capture & grammar evolution | **019B** | Judgment call | Open |
| X38-DFL-04 | Contamination boundary for the discovery loop | **019A** | Thiếu sót | Open |
| X38-DFL-05 | Deliberation-gated code authoring | **019A** | Judgment call | Open |
| X38-DFL-06 | Systematic raw data exploration (10 analyses) | **019C** | Thiếu sót | Open |
| X38-DFL-07 | Raw data analysis methodology (6 categories) | **019C** | Thiếu sót | Open |
| X38-DFL-08 | Feature candidate graduation path (5 stages) | **019D1** | Thiếu sót | Open |
| X38-DFL-09 | SSE-D-02 scope clarification for systematic scan | **019A** | Thiếu sót | Open |
| X38-DFL-10 | Pipeline integration: Stage 2.5 data characterization | **019D1** | Thiếu sót | Open |
| X38-DFL-11 | Statistical budget accounting (two-tier screening) | **019D2** | Thiếu sót | Open |
| X38-DFL-12 | Grammar depth-2 composition (search space expansion) | **019D3** | Thiếu sót | Open |
| X38-DFL-13 | Data trustworthiness & cross-source validation | **019E** | Thiếu sót | Open |
| X38-DFL-14 | Non-stationarity protocol — DGP change detection | **019F** | Thiếu sót | Open |
| X38-DFL-15 | Resolution gap assessment & data acquisition scope | **019G** | Judgment call | Open |
| X38-DFL-16 | Cross-asset context signals for single-asset strategy | **019G** | Judgment call | Open |
| X38-DFL-17 | Pipeline validation via synthetic known-signal injection | **019E** | Thiếu sót | Open |
| X38-DFL-18 | Systematic feature regime-conditional profiling | **019F** | Thiếu sót | Open |

## Files

| File | Purpose |
|------|---------|
| `findings-under-review.md` | **ARCHIVED** — original 18 findings (3005 lines). Kept as reference only. |
| Sub-topic directories | Active debate locations (see split structure above) |
