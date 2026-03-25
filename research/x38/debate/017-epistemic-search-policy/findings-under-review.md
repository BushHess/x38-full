# Findings Under Review — Epistemic Search Policy

**Topic ID**: X38-T-17
**Opened**: 2026-03-24
**Author**: human researcher (external analysis) + claude_code (formatting)

4 findings về Epistemic Search Policy — intra-campaign illumination,
phenotype/structural-prior contracts, inter-campaign promotion ladder,
và budget governor.

**Issue ID prefix**: `X38-ESP-` (Epistemic Search Policy).

**Convergence notes liên quan** (full text tại `../000-framework-proposal/findings-under-review.md`
§Pre-Debate Convergence Notes):
- C-01: MK-17 != primary evidence; firewall = trụ chính
- C-02: Shadow-only principle đã đúng
- C-12: Answer priors bị cấm LUÔN

**Closed topic invariants** (non-negotiable):
- Topic 004 MK-17: Same-dataset empirical priors = shadow-only
- Topic 007 F-01: "Inherit methodology, not answers"
- Topic 007 F-22: Phase 1 evidence taxonomy (3 types frozen)
- Topic 007 F-25: Regime-aware policy: internal conditional logic ALLOWED,
  external classifiers FORBIDDEN
- Topic 001 D-16: protocol_identity_change -> new_campaign (one-way invariant)

---

## ESP-01: Intra-campaign illumination — Stage 3-8 modifications

- **issue_id**: X38-ESP-01
- **classification**: Thiếu sót
- **opened_at**: 2026-03-24
- **opened_in_round**: 0
- **current_status**: Open

**Chẩn đoán**:

Stage 4 hiện tại (F-05) là "Orthogonal pruning -> shortlist.json (keep/drop
ledger)" — thực chất là giữ global top-K rồi đi tiếp. Cách này collapse
diversity quá sớm, biến framework thành máy xếp hạng thay vì máy khám phá.

Evidence: V4->V8 [extra-archive] chạy 5 sessions trên cùng data, mỗi session
tìm winner khác (cùng "D1 slow" family). Framework không ghi lại coverage map
hay phenotype distribution — không ai biết vùng nào đã explore kỹ, vùng nào
bỏ sót.

**Đề xuất sửa Stages 3-8**:

| Stage | Hiện tại (F-05) | Đề xuất bổ sung |
|-------|-----------------|-----------------|
| **3** | Single-feature scan -> registry | + **Descriptor tagging**: gắn mechanism/complexity/turnover/holding descriptors cho mỗi candidate. + **Scan-phase correction**: FDR hoặc cascade design (addresses F-05 open question). + **Coverage map**: grid cells × descriptor dimensions, đánh dấu covered/uncovered. |
| **4** | Orthogonal pruning -> shortlist | **Thay global top-K bằng cell-elite archive**: descriptor cells × vài survivors/cell. Mỗi cell giữ đa dạng (không chỉ best Sharpe). Keep/drop ledger giữ nguyên nhưng ledger ghi lý do per-cell. |
| **5** | Layered architecture -> candidates | + **Local-neighborhood probes**: quanh từng cell survivor, không chỉ layered search. Khám phá adjacency trong descriptor space. |
| **6** | Parameter refinement -> plateau_grids | + **Ép mandatory robustness tests**: ablation, split perturbation, cost sensitivity, plateau-width extraction, dependency tests. Kết quả → contradiction_profile per candidate. |
| **7** | Freeze -> frozen_spec.json | + **Freeze comparison set**: top survivors from mỗi cell (không chỉ winner). + **Freeze coverage map**: final state. + **Freeze phenotype pack**: descriptor + contradiction_profile cho winner + comparison set. |
| **8** | Evaluation -> verdict.json | + **epistemic_delta.json (MANDATORY)**: structured artifact trả lời 4 câu hỏi bắt buộc. |

**epistemic_delta.json** — 4 câu hỏi bắt buộc:

1. **Coverage**: vùng nào của search space đã được cover tốt hơn (cell-level,
   với density metric)?
2. **Robustness**: motif nào robust hơn (wide plateau, low ablation dependency)
   hoặc fragile hơn (narrow plateau, high split sensitivity)?
3. **Contradiction**: prior nào vừa bị phản chứng hoặc thu hẹp phạm vi
   (prior_id + evidence)?
4. **Gap**: vùng nào đáng đổ compute tiếp (uncovered cells, cells with high
   variance, cells adjacent to robust survivors)?

Campaign không nhất thiết thắng về hiệu năng, nhưng **không được kết thúc mà
không biết đã học được gì về search space**. `NO_ROBUST_IMPROVEMENT` + rich
epistemic_delta = campaign thành công về mặt epistemic.

**Tương thích với invariants**:
- F-22 (evidence taxonomy): epistemic_delta nằm ở level coverage/process
  evidence (Type 1 trong F-22). Không claim certification-level status.
- MK-17: Descriptor-level coverage facts KHÔNG phải empirical priors.
  "Cell (SINGLE, LOW_COMPLEXITY, SWING) đã quét 500 configs, best Sharpe 0.3"
  là coverage fact, không phải answer prior.

**Câu hỏi mở**:
- Descriptor taxonomy: bao nhiêu dimensions? Quá ít = không tách biệt, quá
  nhiều = cell explosion (curse of dimensionality)
- Cell-elite archive: bao nhiêu survivors/cell? Fixed hay adaptive?
- epistemic_delta.json: mandatory hay advisory? (Đề xuất: mandatory cho Stage 8
  completion, nhưng content là descriptive, không prescriptive)
- Coverage map format: grid hay hierarchy? Cần asset-agnostic?
- Stage 5 local probes: bao nhiêu probes per cell? Compute budget capped?

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
  structural priors from ESP-02 operate within existing 4-category + UNMAPPED
  boundary, subject to reconstruction-risk gate.
- V4->V8 contamination logs [extra-archive]: every online session leaked answer
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
- STRUCTURAL_PRIOR: new firewall category hay subcategory của existing?
  (Topic 002 must decide)

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
  (Bám Topic 010: "underpowered không được phán tay")
- Demotion: contradiction ĐỦ lực (vượt power floor) → drop 1 rung.
  Contradiction KHÔNG đủ lực → flag REVIEW_REQUIRED, giữ rung hiện tại.
- DEFAULT_METHOD_RULE có thể bị override bởi human researcher (Tier 3 authority
  trong 3-tier model).

**v1 reality check**:

Trên BTC/USDT single-asset, single-dataset (2017-2026): context distance = 0
cho mọi same-dataset campaign. Kết quả:
- Mọi prior kẹt ở OBSERVED hoặc REPLICATED_SHADOW
- ACTIVE và DEFAULT_METHOD_RULE **inert trong v1**
- Ladder infrastructure tồn tại nhưng không trigger

**Argument for building anyway**: v1 campaigns produce phenotype data và populate
OBSERVED/REPLICATED_SHADOW entries. Khi genuinely new data arrives (2027+) hoặc
new asset campaign starts, ladder đã có evidence backlog ready to promote. Không
build ladder = mất evidence accumulation window.

**Argument against**: YAGNI. Build when v2 actually needs it. v1 chỉ cần
epistemic_delta.json + phenotype archive. Ladder logic thêm complexity cho zero
v1 benefit.

**Tương thích với invariants**:
- MK-17: same-dataset = shadow-only → v1 ladder giới hạn tự nhiên
- Topic 007 F-22: Phase 1 evidence ceiling = coverage/process hoặc deterministic
  convergence → ladder promotions beyond REPLICATED_SHADOW cần Phase 2 evidence
- Topic 001 D-16: protocol_identity_change -> new_campaign → ladder demotion/
  review triggered by campaign boundary

**Câu hỏi mở**:
- Build ladder v1 (YAGNI risk) hay defer to v2 (evidence loss risk)?
  Đề xuất: v1 IMPLEMENT storage (OBSERVED, REPLICATED_SHADOW) + v1 DEFER
  activation logic (ACTIVE, DEFAULT_METHOD_RULE). Minimum viable: ghi nhận,
  chưa hành động.
- Context distance measurement: appended data months? Different asset? Different
  market regime? Cần formal definition.
- Power floor cho promotion: reuse Topic 010 F-24 thresholds hay cần riêng?

---

## ESP-04: Budget governor & anti-ratchet mechanism

- **issue_id**: X38-ESP-04
- **classification**: Thiếu sót
- **opened_at**: 2026-03-24
- **opened_in_round**: 0
- **current_status**: Open

**Nội dung**:

Nếu ESP ảnh hưởng search budget (ORDER_ONLY, BUDGET_ONLY), cần guard chống
**ratchet effect**: active prior suppress vùng → vùng không sinh evidence mới →
prior sống sót vì không ai phản chứng → suppress mạnh hơn.

Đây là rủi ro thật: MK-16 (ratchet risk, deferred v2+ trong Topic 004) đã
nhận diện nhưng chưa có mitigation mechanism cụ thể. Đồng thời, Topic 004
C3 (converged) đã chốt: **"Budget split = v2+ design. V1: all search is
frontier."** ESP-04 xây trên nền tảng C3 đã chuẩn bị — nó là implementation
cụ thể cho budget split mà 004 đã defer.

**3 ngăn budget bắt buộc**:

| Ngăn | Mục đích | Constraint |
|------|----------|------------|
| **coverage_floor_budget** | Đảm bảo MỌI descriptor-cell được quét tối thiểu | Không prior active nào được ép một cell rơi dưới floor. Floor = đủ để test ít nhất 1 representative mạnh + 1 ablation + 1 paired comparison. |
| **exploit_budget** | Compute dồn vào vùng promising (prior-guided) | Capped by residual after coverage floor. Không vượt X% total budget (X cần debate). |
| **contradiction_resurrection_budget** | Dành riêng cho phản chứng priors đang active | Mỗi prior suppressing phải tự tài trợ quyền bị phản chứng: asymmetric burden. Budget = đủ coverage obligation cho vùng bị suppress. |

**Luật vận hành**:

1. **Coverage obligation**: "Đủ budget" không tính bằng % tùy tiện mà bằng
   coverage obligation: đủ để test ít nhất 1 representative mạnh + 1 ablation
   + 1 paired comparison per cell.
2. **Cell split rule**: Nếu cell quá rộng để coverage obligation có nghĩa
   (>1000 configs/cell), phải split lại cell. Không dùng sự mơ hồ đó để
   giữ prior sống.
3. **Periodic audit**: Vùng bị suppress > N campaigns liên tiếp → trigger
   full-budget audit (1 campaign chạy full coverage floor trên vùng đó).
   N cần debate.
4. **Suppress transparency**: Mọi budget reduction per cell phải ghi rõ:
   which prior, which evidence, when, how to reverse.

**Tương thích với invariants**:
- MK-17: Budget governor trên same-dataset chỉ ảnh hưởng ordering, không inject
  answer priors. Coverage floor ÉP quét cả vùng mà same-dataset prior suggests
  "yếu" — conservative by design.
- Topic 004 C3 (converged): "Budget split = v2+ design. V1: all search is
  frontier." ESP-04 v1 coverage_floor + exploit_budget là v1-compatible
  implementation — all search remains frontier, budget governor chỉ ảnh hưởng
  ordering/depth trong frontier, không tạo probe lane riêng.
- Topic 004 MK-16 (deferred v2+): Ratchet risk mitigation. Budget governor
  là implementation cụ thể cho MK-16 concern.
- Topic 013 CA-02 (stop conditions): Budget governor interacts với campaign stop
  conditions — coverage floor obligation có thể extend campaign nếu chưa đủ.

**v1 implementation**:

v1 scope giới hạn: ESP chỉ ảnh hưởng intra-campaign ordering/budget.
Budget governor v1:
- coverage_floor_budget: **IMPLEMENT** — Stage 3 scan phải cover mọi cell
  trên floor. Simple: equal allocation + floor per cell.
- exploit_budget: **IMPLEMENT** — Stage 5 probes guided by Stage 4 cell-elite
  results. Capped at 50% of Stage 5 compute (rest = exploration).
- contradiction_resurrection_budget: **DEFER v2** — chỉ có ý nghĩa khi có
  active priors (requires ACTIVE_STRUCTURAL_PRIOR rung, v2 only).

**Câu hỏi mở**:
- Coverage floor per cell: absolute (N configs) hay relative (top-X% of cell)?
- Exploit budget cap: 50%? 70%? Evidence-based calibration method?
- Periodic audit frequency: every N campaigns or when suppress duration > M?
- Cell granularity: quá thô = no discrimination, quá mịn = cell explosion.
  Interaction với ESP-01 descriptor dimensions.
- Budget governor interaction với Topic 013 stop conditions: coverage floor
  chưa đạt → stop campaign? Hay extend?
- **Framework evaluation criteria** (cross-cutting, applies to all ESP findings):
  017 defines mechanism but not acceptance test. To prove ESP "tăng xác suất
  tìm lời giải mạnh", minimum comparison needed: frontier-only vs ESP-enhanced
  under same compute budget, measuring P(INTERNAL_ROBUST_CANDIDATE), comparison
  set diversity, contradiction yield, and outcome on appended data / Clean OOS.
  Aspiration metric: P(strong solution) = P(IRC) × P(CLEAN_OOS | IRC). This is
  a v2+ evaluation (requires multiple campaigns + new context), but criteria
  should be pre-registered now so framework design can accommodate measurement.

---

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 008 | F-02 | 017 proposes ESP as sub-component (v1) -> pillar (v2). If 008 decides 3 pillars sufficient, ESP substance folds into Protocol Engine without architectural promotion. | 008 owns pillar decision; 017 provides substance regardless of framing. |
| 002 | F-04 | Reconstruction-risk gate extends firewall enforcement to phenotype layer. STRUCTURAL_PRIOR may need 5th whitelist category. Topic 002 **actively owns** the ~10 Tier-2 priors gap (MK-07 amendment → 002 debate outcome). ESP-02's STRUCTURAL_PRIOR proposal aligns directly with 002's existing workload. | 002 owns admissibility + gap fix; 017 defines phenotype requirements + reconstruction-risk gate. |
| 003 | F-05 | Cell-elite archive changes Stage 4 design. epistemic_delta.json adds Stage 8 mandatory output. Descriptor tagging adds Stage 3 output. | 003 owns pipeline structure; 017 defines ESP component contracts. |
| 006 | F-08 | Phenotype descriptor taxonomy overlaps feature family taxonomy. | 006 owns feature-level; 017 owns strategy-level. Must not conflict. |
| 010 | F-24 | Power floors for promotion ladder reuse Clean OOS power methodology. | 010 owns power rules; 017 consumes. |
| 013 | CA-01 | Coverage metrics overlap. Budget governor interacts with stop conditions. | 013 owns convergence/stop; 017 defines coverage obligations. |
| 015 | F-14, F-17 | ESP introduces 5+ new mandatory artifacts (epistemic_delta.json, coverage_map, phenotype_pack, comparison_set, prior_registry). F-14 (state pack) must enumerate them; F-17 (semantic change) must classify when changes to ESP artifacts invalidate results. | 015 owns artifact enumeration + invalidation rules; 017 defines artifact contracts + mandatory status. |
| 016 | BR-01 | ESP MUST NOT suggest parameter directions — that would be answer-level influence, incompatible with firewall (C-12). ESP treats recalibrated algo as new phenotype entry. | Explicit scope exclusion in 017. |

## Bảng tổng hợp

| Issue ID | Finding | Phân loại | Status |
|----------|---------|-----------|--------|
| X38-ESP-01 | Intra-campaign illumination (Stages 3-8) | Thiếu sót | Open |
| X38-ESP-02 | CandidatePhenotype & StructuralPrior contracts | Thiếu sót | Open |
| X38-ESP-03 | Inter-campaign promotion ladder | Judgment call | Open |
| X38-ESP-04 | Budget governor & anti-ratchet | Thiếu sót | Open |
