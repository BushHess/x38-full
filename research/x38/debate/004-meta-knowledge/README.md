# Topic 004 — Meta-Knowledge Governance

**Topic ID**: X38-T-04
**Opened**: 2026-03-18
**Closed**: 2026-03-21
**Status**: **CLOSED** — 6 rounds, 23/23 issues resolved. Xem `final-resolution.md`.
**Depends on**: None (parallel with 000)
**Blocks**: 003 (protocol engine needs meta-knowledge rules finalized)

## Core Question

How should meta-knowledge (methodology lessons) be classified, inherited,
challenged, and retired across campaigns — without implicitly leaking
data-derived conclusions disguised as "universal methodology"?

## Problem Brief

Framework chạy nhiều campaigns qua thời gian. Mỗi campaign học được điều gì đó.
**Mang gì sang campaign sau, và mang như thế nào, để không lặp sai lầm cũ nhưng
cũng không khoá chết hướng tìm kiếm mới?**

**Ví dụ cụ thể**: V4 thử multi-layer systems, thất bại trên BTC → V6 viết lesson
"layering is a hypothesis, not a default" → V8 absorb thành hard rule với 7
sub-rules → AI chạy V8 **không thử** multi-layer. Nhưng nếu chạy trên ETH với
order flow data, multi-layer có thể đúng. Rule đã khoá một hướng tìm kiếm mà
không ai nhận ra. Nhân rộng ra qua 10 campaigns, 5 assets, 50 lessons — vấn đề
tích luỹ đến mức framework chỉ xác nhận kết luận cũ thay vì khám phá.

### Chúng ta đã có (chẩn đoán + hướng đi)

- **5 hại cụ thể** của maturity pipeline hiện tại, có ví dụ thực (MK-02)
- **Fundamental constraint**: bias-variance tradeoff ở meta-level — không triệt
  tiêu được, chỉ tìm điểm cân bằng (MK-03)
- **3 loại leakage**: parameter (must = 0) / structural (acceptable if explicit) /
  attention (unavoidable, net-positive) (MK-06)
- **Derivation Test**: phân loại rule bằng "suy ra từ toán thuần được không?" (MK-04)
- **3-Tier Taxonomy**: Axiom (vĩnh viễn) / Structural Prior (có hạn, thách thức
  được) / Session-specific (tự huỷ) (MK-05)

### Chúng ta CHƯA có (8 câu hỏi cần debate — Group C)

1. **Ai phân loại?** AI tự classify rule của mình = conflict of interest. Human
   review mỗi rule = không scale. → MK-08
2. **Challenge mechanism?** Challenge bao nhiêu là đủ? Quá nhiều → Tier 2 vô dụng.
   Quá ít → giống V8 hiện tại. → MK-09
3. **Expiry cụ thể?** Sau bao nhiêu campaigns không gặp failure mode thì rule
   expire? Ai quyết định? → MK-10
4. **Conflict resolution?** Lessons xung đột giữa campaigns (khác asset, khác
   regime). Precedence rules? Scope tags? → MK-11
   ⚠️ **Gap**: Proposal §8 (active cap) mapped → MK-11, nhưng chỉ giải quyết
   selection (chọn 8 từ N), không giải quyết **semantic conflict** khi 2 rules
   active cùng scope-match nhưng nói ngược nhau. Cần debate thêm.
5. **Confidence scoring?** Numeric float (circular — obey = confirm) hay
   qualitative states (ACTIVE/CHALLENGED/CONTESTED/RETIRED)? → MK-12
6. **Storage format?** Machine-readable? Human-readable? Ai đọc, ai viết? → MK-13
7. **Boundary với contamination firewall?** Cả hai đều ngăn "thông tin không nên
   đi qua". Cái gì thuộc firewall, cái gì thuộc meta-knowledge? → MK-14
8. **Bootstrap problem?** Chuyển đổi V4→V8 knowledge (unstructured) sang 3-tier
   taxonomy (structured) như thế nào? → MK-15

## Debate Materials

### Pre-debate inputs (2026-03-19)

Trước khi debate chính thức bắt đầu, đã có một giải pháp đề xuất và phản biện
ban đầu. Cả hai là **input material** cho debate, không phải kết luận.

| Document | Author | Nội dung |
|----------|--------|---------|
| `input_solution_proposal.md` | Human researcher | **Policy Object Model** — giải pháp 12 phần cho 6 câu hỏi mở. Core insight: tách ontology (family nào tồn tại) khỏi policy (family nào được ưu tiên). Lesson chỉ được sửa policy, không ontology. |
| `input_proposal_critique.md` | claude_code | **6 vấn đề** cần giải quyết: compiler không deterministic, auditor circular, budget arbitrary, overlap guard quá mạnh, active cap bias, complexity quá nhiều cho v1. Verdict: hướng đúng, cần refine. |

### Debate status

| Round | Agent | Status |
|-------|-------|--------|
| Pre-debate | Human + claude_code | Input materials ready |
| Pre-debate | claude_code + codex + human | **MK-17 RESOLVED** (Position A: shadow-only on same dataset). **MK-16** mitigations converged (v2+ scope). |
| Rounds 1-2 | claude_code + codex | **Stage 1A CLOSED** — 4 Converged + 5 Judgment call (§14 → human researcher) |
| Rounds 3-6 | claude_code + codex | **Stage 1B CLOSED** — 14/14 resolved (12 Converged + 2 pre-debate) |
| Final | — | **CLOSED** (2026-03-21). Xem `final-resolution.md` |
| Post-closure | Human + claude_code | **MK-07 AMENDED** (2026-03-23). F-06 category coverage investigation: ~10 Tier 2 structural priors have no category home. Interim rule revised (GAP ≠ AMBIGUITY). **RESOLVED by Topic 002** (2026-03-25): no category expansion, permanent `UNMAPPED + Tier 2 + SHADOW` |

### Debate completed

6 rounds hoàn tất (max_rounds_per_topic). 23/23 issues resolved.
V1 governance invariants frozen: D1, D4, D5, D7, D8, D9, MK-08, MK-13, MK-17.
Xem `final-resolution.md` cho full decisions và `judgment-call-deliberation.md` cho 5 judgment calls.

---

## Context

Analysis of the V6→V7→V8 research prompt lineage revealed a de facto
**maturity pipeline**: lessons start in the Meta-knowledge section, then get
absorbed into binding protocol rules in the next version. This mechanism has
measurable benefits (progressive hardening, no section bloat) but also
5 identified harms, one of which is **fundamentally irreducible** (implicit
data leakage through structural rules).

This topic designs the formal governance system for alpha-lab's `knowledge/`
layer — the Meta-Updater pillar (F-02 trụ 3).

## Evidence Base

| Document | Path | Relevance |
|----------|------|-----------|
| V6 meta-knowledge | `x37/docs/gen1/RESEARCH_PROMPT_V6/RESEARCH_PROMPT_V6.md` line 436-447 [extra-archive] | 8 lessons, all absorbed into V7 protocol body |
| V7 meta-knowledge | `x37/docs/gen1/RESEARCH_PROMPT_V7/RESEARCH_PROMPT_V7.md` line 579-586 [extra-archive] | 4 lessons, all absorbed into V8 protocol body |
| V8 meta-knowledge | `x37/docs/gen1/RESEARCH_PROMPT_V8/RESEARCH_PROMPT_V8.md` line 635-643 [extra-archive] | 5 new lessons |
| V8 handoff prompt | `x37/docs/gen1/RESEARCH_PROMPT_V8/PROMPT_FOR_V8_HANDOFF.md` line 7 [extra-archive] | "Transfer only meta-knowledge, NOT data-derived specifics" |
| V6 handoff | `x37/docs/gen1/RESEARCH_PROMPT_V6/PROMPT_FOR_V6_HANDOFF.md` line 19 [extra-archive] | Same principle |
| F-06 (000 findings) | `debate/004-meta-knowledge/findings-under-review.md` (MK-06→MK-08) | Initial 4-category whitelist proposal (content redistributed from 000 after 2026-03-22 split) |
| Conversation 2026-03-18 | Human + Claude Code analysis [no file archive] | Maturity pipeline observation, 5 harms, 3-tier taxonomy proposal |

## Findings (17 issues)

See `findings-under-review.md` for all 17 issues, organized in 3 groups:

**Group A — Problem analysis** (MK-01 to MK-03):
- MK-01: Maturity pipeline observation (de facto mechanism in V6→V7→V8)
- MK-02: Five harms of the maturity pipeline
- MK-03: Fundamental constraint (learning vs independence — irreducible)

**Group B — Proposed solutions** (MK-04 to MK-07):
- MK-04: Derivation Test (classification mechanism)
- MK-05: 3-Tier Rule Taxonomy (axiom / structural prior / session-specific)
- MK-06: Three types of leakage (parameter / structural / attention)
- MK-07: Reconciliation with F-06 (4-category whitelist + tier = 2 dimensions)

**Group C — Operational design** (MK-08 to MK-17):
- MK-08: Lesson lifecycle (creation → classification → review → active → retire)
- MK-09: Tier 2 challenge process (when, how, limits)
- MK-10: Tier 2 expiry mechanism (triggers, timing)
- MK-11: Conflict resolution between lessons
- MK-12: Confidence scoring (numeric vs qualitative)
- MK-13: Storage format (JSON / Markdown / hybrid)
- MK-14: Boundary with Contamination Firewall (topic 002)
- MK-15: Bootstrap problem (seeding first campaign with V4-V8 lessons)
- MK-16: Ratchet risk — Tier 2 rules self-protect by limiting disconfirming evidence *(from external review)*
- MK-17: Central question — same-dataset empirical priors pre-freeze influence *(from external review)*
