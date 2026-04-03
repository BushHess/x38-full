# Findings Under Review — Inter-Campaign ESP (v2 Scope)

**Topic ID**: X38-T-17B
**Opened**: 2026-04-03
**Author**: human researcher (external analysis) + claude_code (formatting)
**Origin**: Split from Topic 017 (2026-04-03). ESP-02, ESP-03, SSE-08-CON
extracted as v2-scope inter-campaign memory decisions.

3 findings about inter-campaign phenotype memory — phenotype/structural-prior
contracts, promotion ladder, and contradiction consumption semantics.

**Issue ID prefix**: `X38-ESP-` (Epistemic Search Policy) and `X38-SSE-`
(Search Space Expansion, inherited from Topic 018).

**Convergence notes liên quan** (full text tại `../000-framework-proposal/findings-under-review.md`
§Pre-Debate Convergence Notes):
- C-01: MK-17 != primary evidence; firewall = trụ chính
- C-02: Shadow-only principle đã đúng
- C-12: Answer priors bị cấm LUÔN

**Closed topic invariants** (non-negotiable):
- Topic 004 MK-17: Same-dataset empirical priors = shadow-only
- Topic 007 F-01: "Inherit methodology, not answers"
- Topic 007 F-22: Phase 1 evidence taxonomy (3 types frozen)
- Topic 001 D-16: protocol_identity_change -> new_campaign (one-way invariant)

**017A outputs consumed** (frozen after 017A closure):
- Cell-axis categories (SSE-04-CELL) — defines dimensions for phenotype descriptors
- Descriptor taxonomy (ESP-01) — defines what descriptors exist
- Coverage map format (ESP-01) — defines how coverage is recorded
- Budget governor rules (ESP-04) — constraints on contradiction resurrection budget

---

## ESP-02: CandidatePhenotype & StructuralPrior contracts

- **issue_id**: X38-ESP-02
- **classification**: Thiếu sót
- **opened_at**: 2026-03-24
- **opened_in_round**: 0
- **current_status**: Open

**Nội dung**:

Cái cần lưu trữ giữa campaigns KHÔNG phải winner memory, mà là **phenotype
memory**. Hai artifacts bắt buộc:

### A. CandidatePhenotype

Sanitized descriptor-level summary of a candidate, stripped of all identifying
information. Schema-level contract — consistent with repo precedent where debate
files already contain typed schemas (Topic 002: `MetaLesson` typed enum,
Topic 010: `CleanOOSConfig` dataclass, Topic 011: `algo_version`/`deploy_version`
component spec). Specific field values subject to debate; structural constraints
frozen ngay:

**Required properties**:
- Campaign/session/protocol provenance (traceable)
- Descriptor bundle (mechanism, complexity, turnover, holding, timeframe,
  regime logic, calibration sparsity, plateau width, cost elasticity,
  ablation dependency, performance equivalence class)
- Contradiction profile (split sensitivity, perturbation fragility)
- Reconstruction-risk score (0.0-1.0) — xem bên dưới
- **Forbidden payload** (NEVER stored):
  - feature_names, lookbacks, thresholds, winner_ids
  - raw_family_labels, exact_parameter_manifold

**Reconstruction-risk gate** (CRITICAL):

Nhiều descriptor bundles nghe "trừu tượng" nhưng thực tế suy ngược ra đúng
một family hoặc một winner. Ví dụ trên BTC/USDT hiện tại: (SINGLE +
LOW_COMPLEXITY + SLOW_HOLDING + D1_CROSS_TF + INTERNAL_REGIME_GATE +
WIDE_PLATEAU) có reconstruction_risk gần 1.0 vì nó uniquely identifies
E5_ema21D1 trong search space đã biết.

**Gate rule**: Nếu phenotype không đạt reconstruction_risk < threshold (debate
cần chốt threshold), nó KHÔNG được promote qua shadow-only. Phải:
- Coarsen descriptors (merge cells) cho đến khi ambiguity đủ
- HOẶC giữ ở shadow-only vĩnh viễn

**Tại sao gate này bắt buộc**: Không có reconstruction-risk gate, phenotype
memory là backdoor qua firewall. Bạn đang lách contamination bằng mô tả vòng
vo. Gate này align với F-04 (typed schema + whitelist) và MK-17 (shadow-only
trên same dataset) — nó là enforcement mechanism cho phenotype layer.

### B. StructuralPrior

Knowledge object rút ra từ phenotype patterns, dùng để ảnh hưởng search policy
ở campaign sau. Contract cứng:

**Required properties**:
- Source phenotype IDs + evidence IDs (traceable)
- Protocol version + dataset identity + contamination lineage
- Required context distance (minimum for activation)
- Power floor reference (minimum statistical power for promotion)
- Activation scope: SHADOW | ORDER_ONLY | BUDGET_ONLY | DEFAULT_METHOD
- Contradiction trigger + expiry trigger
- Semantic validity scope (conditions under which prior remains valid)
- **Forbidden payload** (NEVER stored):
  - feature_names, lookbacks, thresholds, winner_ids

**Tương thích với invariants**:
- MK-17: StructuralPrior trên same-dataset = activation_scope SHADOW only.
  Active promotion chỉ khi context distance > 0 (appended data, new asset).
- F-04 (firewall): forbidden_payload list = firewall content rules applied
  to phenotype layer.
- MK-08 (3-axis lifecycle): StructuralPrior lifecycle tracks via
  constraint_status / semantic_status / lifecycle_state — reuses 004 design.

**Evidence**:
- Topic 004 MK-07 (amended 2026-03-23, **resolved by 002 closure 2026-03-25**):
  ~10 Tier 2 structural priors have no category home. Topic 002 declined category
  expansion; permanent `UNMAPPED + Tier 2 + SHADOW` governance path chosen.
  `STRUCTURAL_PRIOR` as 5th whitelist category was NOT added. Phenotype-derived
  structural priors from ESP-02 operate within existing 3-category + UNMAPPED
  boundary (3 categories after STOP_DISCIPLINE→ANTI_PATTERN consolidation),
  subject to reconstruction-risk gate.
- research/x37/docs/gen1/RESEARCH_PROMPT_V6/CONTAMINATION_LOG_V2.md [extra-archive]: every online session leaked answer
  priors through "methodology" lessons — phenotype contract prevents this by
  enforcing forbidden_payload at schema level

**Câu hỏi mở**:
- Reconstruction-risk threshold: 0.5? Lower? Cần formal definition (information-
  theoretic? Combinatorial? Expert judgment?)
- Reconstruction-risk computation: given search space S and descriptor bundle D,
  how many candidates in S match D? If |match(D, S)| < K, risk too high.
  K depends on |S|.
- Phenotype descriptor dimensions: fixed taxonomy hay extensible? Fixed simpler
  but may not cover all strategy types.

---

## ESP-03: Inter-campaign promotion ladder

- **issue_id**: X38-ESP-03
- **classification**: Judgment call
- **opened_at**: 2026-03-24
- **opened_in_round**: 0
- **current_status**: Open

**Nội dung**:

StructuralPrior cần lifecycle rõ ràng — không phải "có" hay "không" mà là
gradient ảnh hưởng tăng dần theo evidence strength. Đề xuất 4-rung ladder:

```
OBSERVED -> REPLICATED_SHADOW -> ACTIVE_STRUCTURAL_PRIOR -> DEFAULT_METHOD_RULE
```

**Định nghĩa**:

| Rung | Điều kiện | Activation scope | Ví dụ |
|------|-----------|-----------------|-------|
| **OBSERVED** | 1 campaign thấy tín hiệu descriptor-level | SHADOW only | "SINGLE+LOW campaigns tìm robust survivors 3/3 lần" |
| **REPLICATED_SHADOW** | Lặp lại qua 2+ campaigns, chưa đủ context distance hoặc power | SHADOW only | "Pattern lặp lại trên same dataset, 2 campaigns" |
| **ACTIVE_STRUCTURAL_PRIOR** | Replication qua context độc lập hơn (appended data, new snapshot) + không có contradiction đủ lực + vượt power floor | ORDER_ONLY hoặc BUDGET_ONLY | "Pattern lặp trên BTC 2017-2026 VÀ BTC 2017-2027 (appended)" |
| **DEFAULT_METHOD_RULE** | Sống sót qua nhiều context + ít nhất 1 vòng new-data adjudication có lực | DEFAULT_METHOD | "Luôn quét SINGLE+LOW trước: evidence từ 3 assets + 2 time periods" |

**Quy tắc**:
- Mọi contradiction dưới power floor (Topic 010 F-24) CHỈ được đẩy rule về
  `REVIEW_REQUIRED` — không được promote hay retire bằng cảm giác.
- Demotion: contradiction ĐỦ lực → drop 1 rung.
  Contradiction KHÔNG đủ lực → flag REVIEW_REQUIRED, giữ rung hiện tại.
- DEFAULT_METHOD_RULE có thể bị override bởi human researcher (Tier 3 authority).

**v1 reality check**:

Trên BTC/USDT single-asset, single-dataset (2017-2026): context distance = 0
cho mọi same-dataset campaign. Kết quả:
- Mọi prior kẹt ở OBSERVED hoặc REPLICATED_SHADOW
- ACTIVE và DEFAULT_METHOD_RULE **inert trong v1**
- Ladder infrastructure tồn tại nhưng không trigger

**Argument for building anyway**: v1 campaigns produce phenotype data và populate
OBSERVED/REPLICATED_SHADOW entries. Khi genuinely new data arrives (2027+) hoặc
new asset campaign starts, ladder đã có evidence backlog ready to promote.

**Argument against**: YAGNI. Build when v2 actually needs it. v1 chỉ cần
epistemic_delta.json + phenotype archive. Ladder logic thêm complexity cho zero
v1 benefit.

**Tương thích với invariants**:
- MK-17: same-dataset = shadow-only → v1 ladder giới hạn tự nhiên
- Topic 007 F-22: Phase 1 evidence ceiling → ladder promotions beyond
  REPLICATED_SHADOW cần Phase 2 evidence
- Topic 001 D-16: protocol_identity_change → new_campaign → ladder demotion/
  review triggered by campaign boundary

**Câu hỏi mở**:
- Build ladder v1 (YAGNI risk) hay defer to v2 (evidence loss risk)?
  Đề xuất: v1 IMPLEMENT storage (OBSERVED, REPLICATED_SHADOW) + v1 DEFER
  activation logic (ACTIVE, DEFAULT_METHOD_RULE).
- Context distance measurement: appended data months? Different asset? Different
  market regime? Cần formal definition.
- Power floor cho promotion: reuse Topic 010 F-24 thresholds hay cần riêng?

---

## SSE-D-08/017: Contradiction consumption semantics

- **issue_id**: X38-SSE-08-CON
- **classification**: Thiếu sót
- **opened_at**: 2026-03-26
- **opened_in_round**: 0 (deferred from Topic 018, OI-05, shared with 015)
- **current_status**: Open

**Nội dung**:

Topic 018 decided (confirmed 2026-03-27): contradiction registry is descriptor-level, shadow-only (MK-17).
Topic 015 owns row schema/storage. Topic 017B owns consumption semantics.

Topic 017B owns:
1. How surprise queue references contradiction entries (resurrection trigger)
2. How proof bundle incorporates contradiction profile (5th component)
3. Contradiction resurrection as anomaly axis (SSE-D-05 axis 5)
4. Interaction with cell-elite archive (shadow entries vs active candidates)

**Evidence**:
- `debate/018-search-space-expansion/final-resolution.md` SSE-D-08
- `docs/search-space-expansion/debate/claude/claude_debate_lan_5.md` CL-14

**Câu hỏi mở**:
- When does a contradiction entry qualify for resurrection (new evidence threshold)?
- How does shadow-only status interact with cell-elite archive slot allocation?
- Does contradiction resurrection override budget governor anti-ratchet (017A ESP-04)?
  017A owns budget rules; 017B must define consumption that respects them.

---

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 002 | F-04 | Reconstruction-risk gate extends firewall enforcement to phenotype layer. **RESOLVED**: 002 CLOSED — NO vocabulary expansion. Phenotype within 3-category + UNMAPPED. | 002 CLOSED; 017B designs within constraint. |
| 010 | F-24 | Power floors for promotion ladder reuse Clean OOS power methodology. **RESOLVED**: 010 CLOSED — D-24 method-first contract frozen. | 010 CLOSED; 017B consumes D-24. |
| 015 | F-14, F-17 | ESP introduces new mandatory artifacts (phenotype_pack, prior_registry, comparison_set). 015 must enumerate + classify invalidation. | 015 owns enumeration; 017B defines contracts. |
| 017A | ESP-04 | SSE-08-CON contradiction resurrection may override budget governor anti-ratchet. | 017A owns budget rules; 017B defines consumption that respects them. |

---

## Bảng tổng hợp

| Issue ID | Finding | Phân loại | Status |
|----------|---------|-----------|--------|
| X38-ESP-02 | CandidatePhenotype & StructuralPrior contracts | Thiếu sót | Open |
| X38-ESP-03 | Inter-campaign promotion ladder | Judgment call | Open |
| X38-SSE-08-CON | Contradiction consumption semantics (từ Topic 018) | Thiếu sót | Open |
