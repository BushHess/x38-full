# Topic 017 — Epistemic Search Policy

**Topic ID**: X38-T-17
**Opened**: 2026-03-24
**Status**: OPEN (backlog — activate after Wave 2 prerequisites close)
**Origin**: Structural gap identified via external analysis: x38's 3 pillars are
defensive (prevent contamination, enforce process, record methodology) but lack a
mechanism to systematically improve search efficiency across campaigns. F-02
(Topic 008) explicitly asks "3 pillars enough?" — this topic provides a concrete
answer and design.

## Architectural decision

x38 hiện thiếu cơ chế buộc mỗi campaign để lại **epistemic delta** tái sử dụng
được mà không mang theo đáp án. Framework chống tự lừa mình rất khá, nhưng chưa
phải framework học cách search tốt hơn.

Câu hỏi: cần thêm Epistemic Search Policy component hay 3 trụ đã bao trùm?

## Scope

Topic này quyết định liệu Alpha-Lab cần một **Epistemic Search Policy** (ESP)
component chịu trách nhiệm:

1. **Intra-campaign illumination**: search space coverage tracking, diversity
   preservation trong pruning, mandatory epistemic output artifacts
2. **CandidatePhenotype contract**: sanitized descriptor-level memory (không chứa
   winner identity, parameters, feature names) với reconstruction-risk gate
3. **Inter-campaign promotion ladder**: cách structural priors tăng/giảm ảnh
   hưởng qua các context (shadow → active), bám MK-17 trên same-dataset
4. **Budget governor**: anti-ratchet mechanism ngăn priors suppress vùng search
   space vĩnh viễn

**ESP scope giới hạn nghiêm ngặt** — CHỈ 3 loại ảnh hưởng:
- `ORDER_ONLY`: thứ tự khám phá cells trong scan
- `BUDGET_ONLY`: compute budget phân bổ giữa cells
- `DEFAULT_METHOD`: mặc định phương pháp (high-watermark, phải được override bởi
  human hoặc protocol rule)

ESP **KHÔNG BAO GIỜ** được đụng: metrics, splits, pass thresholds, certification
rules, parameter values, hoặc winner identity.

**v1 framing**: ESP hoạt động như **sub-component của Protocol Engine** (ảnh hưởng
Stages 3-6) + **mandatory output artifact** (epistemic_delta.json tại Stage 8).
Trên same-dataset, inter-campaign promotion bị giới hạn bởi MK-17 (shadow-only).
Promote lên pillar riêng khi v2 bật inter-campaign activation trên new data.

Scope KHÔNG bao gồm:
- Thay đổi certification rules (owned by Topic 010)
- Thay đổi firewall content rules (owned by Topic 002)
- Thay đổi campaign transition law (owned by Topic 001, CLOSED)
- Bounded recalibration (owned by Topic 016)

## Evidence base

**Convergence notes** (shared reference tại `000-framework-proposal/`):
- **C-01**: MK-17 != primary anti-recalibration evidence; firewall = trụ chính
- **C-02**: Shadow-only principle đã đúng
- **C-12**: Answer priors bị cấm LUÔN — ESP phải tôn trọng

**Closed topic decisions**:
- Topic 004 MK-17: Same-dataset empirical priors = shadow-only. ESP trên
  same-dataset CHỈ ảnh hưởng ordering/budget, KHÔNG inject priors.
- Topic 004 C3 (converged): "Budget split = v2+ design. V1: all search is
  frontier." ESP-04 budget governor xây trên nền tảng C3 — implementation
  cụ thể cho budget split mà 004 đã defer.
- Topic 004 MK-07 (amended 2026-03-23, **resolved by 002 closure 2026-03-25**):
  ~10 Tier-2 priors gap. No category expansion; permanent `UNMAPPED + Tier 2 +
  SHADOW`. ESP-02 phenotype contracts operate within this boundary.
- Topic 007 F-01: "Inherit methodology, not answers" — ESP inherits
  descriptor-level search policy, NOT answer-level prior.
- Topic 007 F-22: Phase 1 evidence = coverage/process + deterministic convergence.
  epistemic_delta.json mở rộng evidence taxonomy ở descriptor level, nằm dưới
  certification tier.

**Open topic interactions**:
- Topic 008 F-02: "3 pillars enough?" — 017 cung cấp concrete answer
- Topic 002 F-04: Reconstruction-risk gate mở rộng firewall contract
- Topic 003 F-05: Cell-elite archive thay Stage 4 global pruning;
  epistemic_delta.json thêm vào Stage 8 outputs
- Topic 006 F-08: Descriptor taxonomy cho features/strategies
- Topic 013 CA-01/CA-02: Coverage metrics, descriptor-space convergence
- Topic 010 F-24: Power floors cho promotion ladder

**Empirical evidence** [extra-archive]:
- V4->V8: 5 sessions, 5 khác winners cùng "D1 slow" — framework không học được
  gì ngoài "D1 slow works" (too coarse) giữa các sessions
- Gen3 V1: FAILED (NO_ROBUST_CANDIDATE), 4 structural gaps — mỗi campaign mất
  toàn bộ compute không để lại coverage evidence tái sử dụng
- X12-X19 churn research [extra-archive]: 8 studies, 2 SCREEN_PASS. Static
  suppress ceiling mapped. Ví dụ thực tế về epistemic delta có giá trị cao
- X20-X22 breadth expansion [extra-archive]: Cross-asset portfolio, conviction
  sizing, cost sensitivity. Mỗi study kết thúc với structural insight (BTC
  dominates altcoins, entry features have zero IC, churn filter hurt at <30bps)
  nhưng không có artifact hệ thống ghi lại coverage/contradiction

**Findings**:
- ESP-01: Intra-campaign illumination (Stages 3-8 modifications)
- ESP-02: CandidatePhenotype & StructuralPrior contracts
- ESP-03: Inter-campaign promotion ladder
- ESP-04: Budget governor & anti-ratchet mechanism
- SSE-08-CON: Contradiction consumption semantics (từ Topic 018)
- SSE-04-CELL: Cell-axis values + anomaly thresholds (từ Topic 018)

## Dependencies

- **Hard upstream** (must close before 017 debate):
  - Topic 002 (contamination firewall, **CLOSED** 2026-03-25) — firewall rules
    frozen: 3 F-06 categories, NO STRUCTURAL_PRIOR category, permanent
    UNMAPPED + Tier 2 + SHADOW. ESP-02 phenotype operates within this boundary.
  - Topic 008 (architecture & identity) — need pillar count decision (F-02)
    and identity model (F-13) before ESP positioning
  - Topic 010 (Clean OOS) — need power floors (F-24) for promotion ladder
  - Topic 013 (convergence analysis) — need convergence metrics (CA-01) for
    descriptor-space coverage measurement
- **Provisional upstream** (routed findings, contingent on re-closure):
  - Topic 018 (search-space expansion, REOPENED) — SSE-08-CON and SSE-04-CELL
    routed from 018. Provisional until 018 re-closes under standard 2-agent debate.
- **Hard downstream** (017 must close before):
  - Topic 003 (protocol engine) — pipeline stages need to incorporate
    cell-elite archive, descriptor tagging, epistemic_delta.json

## Wave assignment

**Wave 2.5**: Song song với Topic 016 (bounded recalibration). Cả hai:
- Depend on multiple Wave 2 topics (khác dependency set: 016 cần 001+002+010+011+015, 017 cần 002+008+010+013)
- Must close trước Topic 003 (Wave 3)
- Là cross-cutting decisions ảnh hưởng protocol design

016 và 017 KHÔNG depend lẫn nhau — có thể debate song song trong Wave 2.5.

## Debate plan

- Ước lượng: 2-3 rounds
- **Internal staging** (per Topic 004 precedent — 911 lines debated via 1A/1B/1C):

  **Stage A (v1 scope, Rounds 1-2)**: ESP-01 + ESP-04
  - Cell-elite archive có overcomplicate Stage 4 không?
  - epistemic_delta.json nên mandatory hay optional?
  - Coverage floor budget có ép quá nhiều compute vào vùng chắc chắn yếu?
  - Exploit budget cap: bao nhiêu % hợp lý?
  - Mục tiêu: resolve intra-campaign design (what a campaign produces + how it
    allocates compute). Đây là phần implementable ngay trong v1.

  **Stage B (v2 scope, Rounds 2-3)**: ESP-02 + ESP-03
  - Reconstruction-risk gate thresholds — quá chặt = phenotype vô dụng,
    quá lỏng = lách firewall
  - v1 promotion chỉ đến REPLICATED_SHADOW (same-dataset ceiling) — worth
    building storage infrastructure cho cái chưa activate ngay?
  - ~~STRUCTURAL_PRIOR category cần gì từ Topic 002?~~ **RESOLVED**: 002 CLOSED,
    NO category expansion. Phenotype priors within UNMAPPED + Tier 2 + SHADOW.
  - Mục tiêu: resolve inter-campaign memory contracts. Expected outcome:
    v1 = build storage (OBSERVED + REPLICATED_SHADOW), defer activation logic.

- **Tại sao không tách thành 2 topics**: 4 findings có dependency chain linear
  (ESP-01→02→03→04). Tách tạo hard sequential dependency giữa topics, không
  cho phép parallel debate, chỉ thêm overhead. 345 lines nằm trong vùng an toàn
  so với 004 (911 lines, debated thành công).
- Burden of proof: thuộc bên ĐỀ XUẤT ESP (current design = 3 pillars, proposer
  must show 4th component adds value)

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 008 | F-02 | F-02 asks "3 pillars enough?" — 017 proposes ESP as sub-component (v1) → pillar (v2). Pillar count depends on 008 framing. | 008 owns pillar decision; 017 provides substance. If 008 decides 3 sufficient, 017 substance folds into Protocol Engine. |
| 002 | F-04 | Reconstruction-risk gate extends firewall enforcement to phenotype layer. **RESOLVED**: Topic 002 CLOSED (2026-03-25) — NO vocabulary expansion, NO STRUCTURAL_PRIOR category (Facet A). Permanent: UNMAPPED + Tier 2 + SHADOW. ESP-02 phenotype operates within this boundary. | 002 CLOSED; 017 designs within 3-category + UNMAPPED constraint. |
| 003 | F-05 | Cell-elite archive replaces Stage 4 global pruning. epistemic_delta.json adds Stage 8 output. Descriptor tagging adds Stage 3 output. | 003 owns pipeline structure; 017 defines what ESP component feeds into stages. |
| 006 | F-08 | Descriptor taxonomy for phenotypes overlaps feature family taxonomy. | 006 owns feature-level taxonomy; 017 owns strategy-level descriptors. |
| 013 | CA-01 | Coverage metrics in convergence analysis overlap ESP coverage tracking. | 013 owns convergence metrics; 017 defines coverage obligations for budget governor. |
| 010 | F-24 | Power floors for Clean OOS reused for promotion ladder gates. | 010 owns power rules; 017 consumes them for promotion decisions. |
| 015 | F-14, F-17 | ESP introduces 5+ new mandatory artifacts (epistemic_delta.json, coverage_map, phenotype_pack, comparison_set, prior_registry). F-14 must enumerate; F-17 must classify invalidation. | 015 owns enumeration + invalidation; 017 defines contracts. |
| 004 | C3 | "Budget split = v2+ design. V1: all search is frontier." ESP-04 budget compartments may constitute a budget split. | 017 must reconcile with C3 constraint. |
| 016 | BR-01 | If ESP manages search budget, interaction with bounded recalibration: ESP MUST NOT suggest parameter directions (answer-level influence). | 017 scope explicitly excludes parameter values. If 016 allows recalibration, ESP treats recalibrated algo as new phenotype. |
| 018 | SSE-08-CON, SSE-04-CELL | Contradiction consumption semantics + cell-axis values routed from 018 (REOPENED). Provisional. | 017 owns consumption/values; 018 provides context (provisional). |

## Files

| File | Purpose |
|------|---------|
| `findings-under-review.md` | 6 findings: ESP-01, ESP-02, ESP-03, ESP-04 + 2 from Topic 018 (SSE-08-CON, SSE-04-CELL) |
| `claude_code/` | Critique from Claude Code |
| `codex/` | Critique from Codex |
