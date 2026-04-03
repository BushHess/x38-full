# Findings Under Review — Intra-Campaign ESP (v1 Scope)

**Topic ID**: X38-T-17A
**Opened**: 2026-04-03
**Author**: human researcher (external analysis) + claude_code (formatting)
**Origin**: Split from Topic 017 (2026-04-03). ESP-01, ESP-04, SSE-04-CELL
extracted as v1-implementable intra-campaign decisions.

3 findings about intra-campaign epistemic search policy — illumination
(Stages 3-8 modifications), budget governor (anti-ratchet), and cell-axis
values/anomaly thresholds.

**Issue ID prefix**: `X38-ESP-` (Epistemic Search Policy) and `X38-SSE-`
(Search Space Expansion, inherited from Topic 018).

**Convergence notes liên quan** (full text tại `../000-framework-proposal/findings-under-review.md`
§Pre-Debate Convergence Notes):
- C-01: MK-17 != primary evidence; firewall = trụ chính
- C-02: Shadow-only principle đã đúng
- C-12: Answer priors bị cấm LUÔN

**Closed topic invariants** (non-negotiable):
- Topic 004 MK-17: Same-dataset empirical priors = shadow-only
- Topic 004 C3 (converged): "Budget split = v2+ design. V1: all search is frontier."
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

Evidence: research/x37/docs/gen1/RESEARCH_PROMPT_V8/CONVERGENCE_STATUS_V3.md:14-41 [extra-archive] —
8 sessions (V4-R1→R5, V5, V6, V7) trên cùng data, mỗi session tìm winner khác
(cùng "D1 slow" family). Framework không ghi lại coverage map hay phenotype
distribution — không ai biết vùng nào đã explore kỹ, vùng nào bỏ sót.

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

## SSE-D-04/05/017: Cell-axis values + anomaly thresholds + proof bundle consumption

- **issue_id**: X38-SSE-04-CELL
- **classification**: Thiếu sót
- **opened_at**: 2026-03-26
- **opened_in_round**: 0 (deferred from Topic 018, SSE-D-04/05)
- **current_status**: Open

**Nội dung**:

Topic 018 decided (confirmed 2026-03-27): 4 mandatory cell axes (`mechanism_family`, `architecture_depth`,
`turnover_bucket`, `timeframe_binding`). 5 anomaly axes for surprise queue admission
(≥1 non-peak-score). 5-component proof bundle minimum.

Topic 017A owns:
1. Exact values/categories for each of the 4 cell axes
2. Numeric thresholds for each of the 5 anomaly axes
3. Proof bundle consumption rules (what constitutes "passing" a proof component)
4. Cell-elite capacity per cell and surprise slot allocation (capped 20% per evidence)
5. Shared with 013: equivalence/correction thresholds

**Evidence**:
- `debate/018-search-space-expansion/final-resolution.md` SSE-D-04 field 1, SSE-D-05
- `docs/search-space-expansion/debate/claude/claude_debate_lan_6.md` CL-19 field 1
- `docs/search-space-expansion/debate/claude/claude_debate_lan_5.md` CL-17

**Câu hỏi mở**:
- How many categories per cell axis? (e.g., mechanism_family: {momentum, mean_reversion, ...})
- Anomaly thresholds: absolute (ρ < 0.3) or relative (< cell median)?
- Proof bundle: pass/fail per component or composite score?
- Cell-elite capacity: fixed K per cell or adaptive?

---

## 013↔017 Circular Dependency — Resolution Strategy

> **Added 2026-03-31 (gap audit)**. This is NOT a finding — it is a structural
> note documenting how the circular dependency between Topics 013 and 017 must
> be resolved before either topic's deferred numerics can be finalized.

**The circle**:
- Topic 013 (CLOSED) deferred item 3a numerics (robustness bundle minimum),
  3b (consumption sufficiency), and item 4 (anomaly numerics) because they
  need Topic 017's consumption framework.
- Topic 017A (OPEN) needs Topic 013's production metrics to define what
  constitutes "passing" proof.

**Resolution approach**: Topic 017A debate MUST explicitly address the 013-deferred
items as **INTERFACE CONTRACTS** — defining:

1. **What 013 produces** (production schema): robustness bundle format, anomaly
   score format, equivalence metric format. These are already partially defined
   in 013's final-resolution (structural part frozen).

2. **What 017A consumes** (consumption contract): minimum proof components,
   passing criteria, cell-elite admission thresholds. This is what 017A must
   freeze.

3. **Joint reconciliation**: After 017A closes, 013's deferred numerics (3a, 3b,
   item 4) become resolvable. These must be **explicitly resolved** as a
   post-017A integration step — NOT silently assumed "done" by 017A closure.
   Recommended: create a mini-integration finding in Topic 003 (protocol engine)
   that consumes both 013 and 017A outputs.

4. **BH upgrade path**: 013 froze Holm as v1 default, BH contingent on 017's
   proof-consumption guarantee. 017A must explicitly state whether it provides
   this guarantee or BH remains unavailable.

**Who owns this**: Topic 017A debate is the place to break the cycle. Topic 003
(Wave 3) is the integration point. After 017A closes:
- 013 deferred items become resolvable
- 003 performs final integration
- Specs (architecture_spec, methodology_spec) receive reconciled numerics

---

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 003 | F-05 | Cell-elite archive changes Stage 4 design. epistemic_delta.json adds Stage 8 mandatory output. Descriptor tagging adds Stage 3 output. | 003 owns pipeline structure; 017A defines ESP component contracts. |
| 006 | F-08 | Phenotype descriptor taxonomy overlaps feature family taxonomy. | 006 owns feature-level; 017A owns strategy-level. Must not conflict. |
| 013 | CA-01 | Coverage metrics overlap. Budget governor interacts with stop conditions. 013↔017 circular dep on deferred numerics — see resolution strategy above. | 013 owns convergence/stop; 017A defines coverage obligations + breaks cycle. |
| 004 | C3 | "Budget split = v2+ design. V1: all search is frontier." ESP-04 budget compartments may constitute budget split. | 017A must reconcile: ordering within frontier ≠ budget split. |
| 016 | BR-01 | ESP MUST NOT suggest parameter directions — answer-level influence, incompatible with firewall (C-12). | Explicit scope exclusion in 017A. |
| 017B | ESP-02 | 017B needs cell-axis categories from SSE-04-CELL and descriptor taxonomy from ESP-01. | 017A closes first → 017B consumes. |
| 017B | SSE-08-CON | Contradiction resurrection (017B) may override ESP-04 budget governor anti-ratchet (017A). | 017A owns budget rules; 017B defines consumption that respects them. |

---

## Bảng tổng hợp

| Issue ID | Finding | Phân loại | Status |
|----------|---------|-----------|--------|
| X38-ESP-01 | Intra-campaign illumination (Stages 3-8) | Thiếu sót | Open |
| X38-ESP-04 | Budget governor & anti-ratchet | Thiếu sót | Open |
| X38-SSE-04-CELL | Cell-axis values + anomaly thresholds (từ Topic 018) | Thiếu sót | Open |
