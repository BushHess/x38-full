# Debate Index — X38

Chỉ mục toàn cục cho các topic đang được tranh luận.

**Cập nhật**: 2026-04-01 — Audit sync: Topic 019 updated 12→18 findings (DFL-13→18),
total 75→81. Propagated gap audit findings to READMEs (003, 006, 012, 014).
PLAN.md + EXECUTION_PLAN.md partially synced (topic-level detail for 019 added;
aggregate counts and draft status were NOT updated — corrected 2026-04-01 audit fix).
architecture_spec traceability typo fixed (4→3 categories).
methodology_spec.md added to drafts/README. Missing claude_code/codex dirs created (014, 015).
Previous: 2026-03-31 — Gap audit: 5 new findings added (F-36, F-37, F-38, F-39, ER-03),
F-19 demoted to supporting evidence, 013↔017 resolution strategy added to 017,
DFL-07 scope note added, B-02 contradiction escalated in 011/015.
Previous: 2026-03-31 — Topic 019 updated to 12 findings (DFL-01→DFL-12), later expanded to 18 (DFL-13→DFL-18 added same day).
Added: DFL-12 Grammar Depth-2 Composition (search space expansion, operator
whitelist, SSE-D-02 spirit question). DFL-11 corrected (MI pre-filter NOT free,
budget K_max is empirical). Decision summary added (14 decisions in 3 tiers).
Decision-framing added to DFL-01, DFL-02, DFL-06. File structure fixed.
Previous: 2026-03-31 — Topic 019 updated to 10 findings (DFL-01→DFL-10).
Added: raw data exploration (06/07), feature graduation path (08), SSE-D-02 scope
clarification (09), pipeline integration (10: Stage 2.5 Data Characterization).
Previous: 2026-03-29 — Topic 019 OPENED (discovery feedback loop, Wave 2.5).
Previous: 2026-03-28 — Topic 013 CLOSED (6 rounds canonical + 12 rounds JC-debate. 4 Judgment call.
Hybrid C convergence framework, bootstrap defaults with 5-tier provenance, Holm correction law,
equivalence thresholds. Unblocks Topic 017).
Previous: 2026-03-27 — Topic 018 CLOSED (6 rounds standard 2-agent. 10 Converged + 1 Judgment call.
Downstream routing confirmed to 006/015/017/013/008/003).
Previous: 2026-03-27 — Topic 008 CLOSED (8 rounds, 4/4 resolved: 4 Converged).
Previous: 2026-03-26 — Topic 018 REOPENED (governance: 4-agent extra-canonical debate
does not satisfy x38_RULES.md §5; requires standard 2-agent debate).
Previous: 2026-03-26 — Topic 018 CLOSED (7 rounds, 4 agents, 10/10 resolved: 7 Converged + 3 Defer).
Previous: 2026-03-25 — Topic 010 CLOSED (6 rounds, 4/4 resolved: 3 Converged + 1 Judgment call).
Previous: 2026-03-25 — Topic 002 CLOSED (6 rounds, 7/7 resolved: 3 Converged + 4 Judgment call).
Previous: 2026-03-24 — Topic 017 added (epistemic search policy, Wave 2.5).
Previous: 2026-03-23 — Topic 001 CLOSED (6 rounds, 3/3 resolved: 2 Converged + 1 Judgment call).
Topic 016 added (bounded recalibration path, Wave 2.5).
rules.md amended: Cross-topic tensions section bắt buộc (§21-24).
Previous: 2026-03-22 — Topic 000 SPLIT thành 11 sub-topics. Topics 013-014
added (gap analysis). Topic 003 split: F-14/F-17 → Topic 015.

## Topic Registry

| Topic ID | Topic | Opened | Status | Dossier | Findings |
|----------|-------|--------|--------|---------|----------|
| X38-T-00 | Framework architecture (index) | 2026-03-18 | **SPLIT** (2026-03-22) | `000-framework-proposal/` | Index + convergence notes C-01→C-12 |
| X38-T-01 | Campaign model | 2026-03-22 | **CLOSED** (2026-03-23) | `001-campaign-model/` | F-03, F-15, F-16 (3) — 2 Converged + 1 Judgment call |
| X38-T-02 | Contamination firewall | 2026-03-22 | **CLOSED** (2026-03-25) | `002-contamination-firewall/` | F-04 (1) — 3 Converged + 4 Judgment call |
| X38-T-03 | Protocol engine | 2026-03-22 | OPEN | `003-protocol-engine/` | F-05, F-36, F-37 + SSE-D-04 (4) |
| X38-T-04 | Meta-knowledge governance | 2026-03-18 | **CLOSED** (2026-03-21) | `004-meta-knowledge/` | 23/23 resolved |
| X38-T-05 | Core engine design | 2026-03-22 | OPEN | `005-core-engine/` | F-07 (1) |
| X38-T-06 | Feature engine design | 2026-03-22 | OPEN | `006-feature-engine/` | F-08, F-38 + SSE-D-03 (3) |
| X38-T-07 | Philosophy & mission claims | 2026-03-22 | **CLOSED** (2026-03-23) | `007-philosophy-mission/` | F-01, F-20, F-22, F-25 (4) — 4/4 Converged |
| X38-T-08 | Architecture & identity | 2026-03-22 | **CLOSED** (2026-03-27) | `008-architecture-identity/` | F-02, F-09, F-13 + SSE-04-IDV (4) — 4/4 Converged |
| X38-T-09 | Data integrity | 2026-03-22 | OPEN | `009-data-integrity/` | F-10, F-11 (2) |
| X38-T-10 | Clean OOS & certification | 2026-03-22 | **CLOSED** (2026-03-25) | `010-clean-oos-certification/` | F-12, F-21, F-23, F-24 (4) — 3 Converged + 1 Judgment call |
| X38-T-11 | Deployment boundary | 2026-03-22 | OPEN | `011-deployment-boundary/` | F-26, F-27, F-28, F-29 (4) |
| X38-T-12 | Quality assurance | 2026-03-22 | OPEN | `012-quality-assurance/` | F-18, F-39 (2 active) + F-19 (demoted to supporting evidence) |
| X38-T-13 | Convergence analysis | 2026-03-22 | **CLOSED** (2026-03-28) | `013-convergence-analysis/` | CA-01, CA-02 + SSE-09, SSE-04-THR (4) — 4 Judgment call |
| X38-T-14 | Execution & resilience | 2026-03-22 | OPEN | `014-execution-resilience/` | ER-01, ER-02, ER-03 (3) |
| X38-T-15 | Artifact & version management | 2026-03-22 | OPEN | `015-artifact-versioning/` | F-14, F-17 + SSE-07, SSE-08, SSE-04-INV (5) |
| X38-T-16 | Bounded recalibration path | 2026-03-23 | OPEN (backlog) | `016-bounded-recalibration-path/` | BR-01, BR-02 (2) |
| X38-T-17 | Epistemic search policy | 2026-03-24 | OPEN (backlog) | `017-epistemic-search-policy/` | ESP-01, ESP-02, ESP-03, ESP-04 + SSE-08-CON, SSE-04-CELL (6) |
| X38-T-18 | Search-space expansion | 2026-03-25 | **CLOSED** (2026-03-27) | `018-search-space-expansion/` | 10 OIs resolved → 11 decisions (OI-02 expands to D-02+D-03). 10 Converged + 1 Judgment call. 6 rounds (standard 2-agent). Downstream routing confirmed to 006/015/017/013/008/003. |
| X38-T-19 | Discovery feedback loop | 2026-03-29 | OPEN | `019-discovery-feedback-loop/` | DFL-01→DFL-18 (18) |

**Totals**: 20 topics (8 CLOSED, 1 SPLIT, 11 OPEN). 81 findings distributed (70 original + 5 gap audit + 6 DFL data-foundation; F-19 demoted; excludes Topic 004 MK-series and Topic 000 convergence notes).
**Note**: Topic 018 downstream routings (SSE-04-IDV→008, SSE-07/08/04-INV→015,
SSE-08-CON/04-CELL→017, SSE-09/04-THR→013) are **confirmed** (018 CLOSED 2026-03-27).

## Debate Waves

```
Wave 1:    007 (philosophy)              ← NỀN TẢNG, debate đầu tiên
               ↓
Wave 2:    018✅ (search-space expansion)  ← CLOSED (2026-03-27), routings confirmed to 6 downstream topics
           008✅, 009, 010✅, 011, 012    ← song song sau 007 (008: SSE-04-IDV confirmed, 018✅)
           001✅, 002✅, 005, 006          ← song song sau 007 (006: SSE-D-03 confirmed, 018✅)
           013✅ (convergence)             ← CLOSED (2026-03-28), unblocks 017 (SSE-09/04-THR confirmed, 018✅)
           015 (artifact/version)         ← song song, soft-dep 007✅, 008✅ (SSE-07/08/04-INV confirmed, 018✅)
               ↓
Wave 2.5:  016 (bounded recalibration)   ← chờ 001✅ + 002✅ + 010✅ + 011 + 015
           017 (epistemic search policy) ← chờ 002✅ + 008✅ + 010✅ + 013✅ (SSE-08-CON/04-CELL confirmed, 018✅) — ALL DEPS SATISFIED
           019 (discovery feedback loop) ← chờ 018✅ + 002✅ + 004✅ — ALL DEPS SATISFIED (song song với 017)
               ↓
Wave 3:    003 (protocol)                ← chờ 001✅ + 002✅ + 004✅ + 015 + 016 + 017 + 019
           014 (execution)               ← chờ 003 + 005
```

**Wave 1** (1 topic): Triết lý và mission claims phải settled trước — mọi topic
khác phụ thuộc.

**Wave 2** (9 remaining topics, song song — 001, 002 closed): Sau khi 007 closed, tất cả topics còn lại
(trừ 003, 014, 016, 017) có thể debate song song. Topics 016 và 017 thuộc Wave 2.5 — xem bên
dưới. Dependencies giữa các Wave 2 topics chỉ là soft — debate có thể tiến hành,
minor adjustments sau nếu cần.
- Topic 013 (convergence) có soft-dep trên 001 (campaign model).
- Topic 015 (artifact/version) có soft-dep trên 007 + 008. Tách từ 003 để
  debate sớm hơn — không cần pipeline stages finalized.

**Wave 2.5** (3 topics): Bounded recalibration path (016), Epistemic search
policy (017), và Discovery feedback loop (019) là cross-cutting decisions.
016 chạm 5 Wave 2 topics (001, 002, 010, 011, 015). 017 chạm 4 Wave 2 topics
(002, 008, 010, 013). 019 kế thừa 018 (bounded ideation, recognition stack) +
002 (firewall) + 004 (meta-knowledge). Cả ba phải close TRƯỚC 003 — 016 vì
recalibration branch, 017 vì cell-elite archive và epistemic_delta.json, 019
vì discovery loop có thể thêm protocol interaction points. 016, 017, và 019
KHÔNG depend lẫn nhau — debate song song.

**Wave 3** (2 topics): Protocol engine (003) là topic tích hợp, phụ thuộc Campaign
model (001), Contamination firewall (002), Meta-knowledge (004, đã closed),
Artifact spec (015), **Bounded recalibration (016)**, **Epistemic search policy (017)**,
**và Discovery feedback loop (019)**. Execution & resilience (014) phụ thuộc
protocol engine (003) và core engine (005).

## Convergence Notes (shared reference)

12 convergence notes từ pre-debate review (C-01→C-12) được giữ tại
`000-framework-proposal/findings-under-review.md`. Mỗi topic mới cite
convergence notes liên quan — không lặp lại full text.

## Pre-debate open questions (O-01→O-05)

5 câu hỏi mở từ pre-debate review, nay phân vào topics:

| ID | Câu hỏi | Topic |
|----|---------|-------|
| O-01 | F-27 boundary: Alpha-Lab vs deployment layer | **011** |
| O-02 | F-20 naming: 3-tier claims | **007** |
| O-03 | F-04 exceptions: firewall valid exceptions | **002** |
| O-04 | F-16 transition law: campaign-to-campaign guardrails | **001** |
| O-05 | F-26 trigger router: general trigger mechanism | **011** |

## Gen4 evidence import (2026-03-21)

5 findings mới (F-13→F-17) imported từ `x37/docs/gen4/`. Phân bổ:
- F-13 → 008 (architecture), F-15 → 001 (campaign)
- F-14, F-17 → **015** (artifact & version management) — originally 003, split 2026-03-22
- F-16 → 001 (campaign model)

## Dependencies (detailed)

```
007 (philosophy) ← foundation for all — CLOSED✅
    ↓
018 (search-space) ← soft-dep from 007✅, 004✅ — CLOSED✅ (2026-03-27, routings confirmed)
008 (architecture) ← soft-dep from 007✅; SSE-04-IDV confirmed (018✅) — CLOSED✅
009 (data) ← soft-dep from 007✅, 008✅
010 (clean-oos) ← soft-dep from 007✅ — CLOSED✅
011 (deployment) ← soft-dep from 007✅, 010✅
012 (quality) ← soft-dep from 007✅, 008✅
001 (campaign) ← soft-dep from 007✅ — CLOSED✅
002 (firewall) ← soft-dep from 007✅, 008✅ — CLOSED✅
005 (core-engine) ← soft-dep from 007✅, 008✅
006 (feature-engine) ← soft-dep from 007✅, 008✅
013 (convergence) ← soft-dep from 007✅, 001✅ — CLOSED✅ (2026-03-28)
015 (artifact/version) ← soft-dep from 007✅, 008✅
    ↓
016 (bounded-recal) ← HARD-dep from 001✅ + 002✅ + 010✅ + 011 + 015
017 (epistemic-SP)  ← HARD-dep from 002✅ + 008✅ + 010✅ + 013✅; confirmed input: 018✅ (SSE-08-CON, SSE-04-CELL) — ALL DEPS SATISFIED
019 (discovery-FL)  ← HARD-dep from 018✅ + 002✅ + 004✅ — ALL DEPS SATISFIED (song song 017)
    ↓
003 (protocol) ← HARD-dep from 001✅ + 002✅ + 004✅ + 015 + 016 + 017 + 019
014 (execution) ← soft-dep from 003, 005
```

## Gap analysis & rebalancing (2026-03-22)

4 findings mới từ gap analysis (renumbered với topic-specific prefixes per rules.md §naming):
- X38-CA-01, X38-CA-02 → 013 (convergence analysis)
- X38-ER-01, X38-ER-02 → 014 (execution & resilience)

Topic 003 rebalanced: F-14, F-17 tách sang 015 (artifact & version management).
Lý do: F-14/F-17 là "records & versioning" (ghi cái gì, khi nào invalid), khác
bản chất với F-05 (pipeline logic). Tách giúp 003 focused + F-14/F-17 debate sớm
hơn (Wave 2 thay vì Wave 3).

## Topic 017 origin (2026-03-24)

Epistemic search policy — structural gap identified via external analysis:
- x38's 3 pillars are defensive (prevent contamination, enforce process, record
  methodology) but lack mechanism to improve search efficiency across campaigns
- F-02 (Topic 008) explicitly asks "3 pillars enough?" — 017 provides answer
- V4->V8 evidence: 5 sessions produced no reusable coverage artifacts
- MK-16 (ratchet risk, deferred v2+) needs implementation mechanism

Rationale cho Wave 2.5: 017 phụ thuộc 4 Wave 2 topics (002, 008, 010, 013)
nhưng phải close trước 003 (protocol engine). Cell-elite archive, descriptor
tagging, và epistemic_delta.json đều ảnh hưởng pipeline stage design. 017 song
song với 016 — khác dependency set, không depend lẫn nhau.

## Topic 016 origin (2026-03-23)

Bounded recalibration path — orphaned cross-cutting question:
- C-04 + C-12 xác nhận x38 chưa có path, prima facie bất tương thích với firewall
- Topic 011 F-26 (line 73) để mở: "full re-discovery hay parameter-only triage?"
- Topic 001 F-16: campaign guardrails chưa cover recalibration trigger
- Không topic nào own trọn quyết định → mở topic riêng (016)

Rationale cho Wave 2.5: 016 phụ thuộc 5 Wave 2 topics nhưng phải close trước 003
(protocol engine). Nếu 016 close sau 003, protocol có thể phải reopen.

Precedent pattern: F-17 ↔ F-27 tension → F-28 + F-29 interface findings.
016 biến xung đột cross-topic thành quyết định kiến trúc rõ ràng.

## Rules amendment (2026-03-23)

rules.md §21-24: Cross-topic tensions section bắt buộc trong mọi topic.
Format: bảng `| Topic | Finding | Tension | Resolution path |`.
Topic owner maintain, cập nhật mỗi round. Không bỏ qua — nếu không có tension
thì ghi "Không có tension đã biết."

## Bắt đầu từ đâu

1. **Topic 007** (philosophy-mission) — debate ĐẦU TIÊN — **CLOSED** (2026-03-23)
2. **Wave 2** (10 remaining topics, 001 closed early) — song song sau khi 007 closed
3. **Wave 2.5**: Topic 016 (bounded-recalibration) + Topic 017 (epistemic-search-policy) + Topic 019 (discovery-feedback-loop) — song song, sau Wave 2 prerequisites
4. **Wave 3**: Topic 003 (protocol-engine) + Topic 014 (execution) — cuối cùng
