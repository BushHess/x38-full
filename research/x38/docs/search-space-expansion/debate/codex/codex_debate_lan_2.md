---
doc_type: debate_round_review
topic: search-space-expansion
round: 2
author: codex
date: 2026-03-26
status: OPEN
sources:
  - ../../request.md
  - ../gemini/gemini_propone.md
  - ./codex_propone.md
  - ../claude/claude_propone.md
  - ../chatgptpro/chatgptpro_propone.md
  - ../gemini/gemini_debate_lan_1.md
  - ./codex_debate_lan_1.md
  - ../claude/claude_debate_lan_1.md
  - ../chatgptpro/chatgptpro_debate_lan_1.md
  - ../../../online_vs_offline.md
  - ../../../design_brief.md
  - ../../../../x38_RULES.md
  - ../../../../debate/rules.md
  - ../../../../debate/003-protocol-engine/findings-under-review.md
  - ../../../../debate/006-feature-engine/findings-under-review.md
  - ../../../../debate/008-architecture-identity/findings-under-review.md
  - ../../../../debate/013-convergence-analysis/findings-under-review.md
  - ../../../../debate/015-artifact-versioning/findings-under-review.md
  - ../../../../debate/017-epistemic-search-policy/README.md
  - ../../../../debate/017-epistemic-search-policy/findings-under-review.md
  - ../../../../debate/002-contamination-firewall/final-resolution.md
  - ../../../../debate/004-meta-knowledge/final-resolution.md
  - ../../../../debate/007-philosophy-mission/final-resolution.md
tracking_rules:
  - Convergence Ledger là nguồn chân lý cho các điểm đã chốt.
  - Vòng sau chỉ bàn các mục trong Open Issues Register.
  - Muốn lật lại điểm đã khóa phải tạo REOPEN-* kèm bằng chứng mới.
  - Ý tưởng mới phải tạo NEW-* và giải thích vì sao issue hiện tại không bao phủ.
  - Không đổi ID cũ, không đánh số lại.
status_legend:
  CONVERGED: đã đủ chắc để không bàn lại.
  PARTIAL: cùng hướng lớn nhưng chi tiết chưa khóa.
  OPEN: còn tranh chấp thực chất.
  DEFER: có giá trị nhưng không nên là trọng tâm v1.
---

# Debate Round 2 — Narrowing v1, Không Ép Hội Tụ Giả

## 1. Kết luận nhanh

Round 2 không thêm `Converged` mới. Delta thật sự là: (1) nếu có AI ideation lane,
nó phải kết thúc trước `protocol lock`, còn runtime vẫn là offline deterministic
pipeline; (2) `Topic 018` không thể mở trong chính session này theo `debate/rules.md`
§12, nên OI-01 chỉ được thu hẹp theo hướng ownership trong các topic hiện có, chưa
được phép "giải quyết" bằng topic mới; (3) backbone intra-campaign vẫn là
`descriptor tagging -> coverage map -> cell-elite archive -> local probes`, còn
domain-seed/prompt-cross-pollination chỉ là feedstock tùy chọn, không phải control
law; (4) proof bundle và negative-memory storage vẫn chưa đủ bằng chứng để khóa
schema tối thiểu, nên phải giữ `PARTIAL` thay vì đánh dấu hội tụ.

Evidence: `docs/online_vs_offline.md`; `debate/rules.md` §7, §12;
`debate/017-epistemic-search-policy/findings-under-review.md` (X38-ESP-01);
`docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_1.md`
(OI-02, OI-03, OI-05, OI-06); `docs/search-space-expansion/debate/codex/codex_debate_lan_1.md`
(OI-01..OI-06).

---

## 2. Scoreboard

| Agent | Bám yêu cầu | Bám X38 | Khả thi v1 | Sức mở search | Kỷ luật contamination | Độ rõ artifact | Verdict ngắn |
|-------|-------------|---------|------------|---------------|----------------------|----------------|--------------|
| Gemini | Trung bình | Tốt | Trung bình | Trung bình | Tốt | Trung bình | Hữu ích như ideation feedstock; không đủ làm backbone |
| Codex | Rất tốt | Rất tốt | Tốt | Tốt | Tốt | Rất tốt | Backbone v1 mạnh hơn sau khi siết scope và không ép 018/019 |
| Claude | Tốt | Trung bình | Yếu | Rất tốt | Trung bình | Tốt | Câu hỏi "Who writes VDO?" còn giá trị; `Phase A/Topic 018` vẫn quá rộng cho round 2 |
| ChatGPT Pro | Rất tốt | Rất tốt | Rất tốt | Tốt | Rất tốt | Rất tốt | Guardrail và critical-path baseline tốt nhất; vẫn cần lineage/equivalence từ Codex |

Evidence: `docs/search-space-expansion/debate/claude/claude_debate_lan_1.md`
(self-critique về GFS scale, SSS contamination, Topic 018 scope);
`docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_1.md`
(baseline `017-first`); `docs/search-space-expansion/debate/gemini/gemini_debate_lan_1.md`
(OI-01..OI-03).

---

## 3. Convergence Ledger

Không thêm `Converged` mới ở round 2. Giữ nguyên ledger của round 1 để tránh vi
phạm `debate/rules.md` §7-§9.

| ID | Kết luận hội tụ | Basis | Status | Ghi chú |
|----|----------------|-------|--------|---------|
| CL-01 | Promise của framework vẫn là tìm candidate mạnh nhất trong declared search space hoặc kết luận `NO_ROBUST_IMPROVEMENT`; topic này không được lén đổi promise đó | `debate/007-philosophy-mission/final-resolution.md` | CONVERGED | Imported from CLOSED Topic 007 |
| CL-02 | Same-dataset empirical priors vẫn shadow-only pre-freeze | `debate/004-meta-knowledge/final-resolution.md` (MK-17) | CONVERGED | Imported from CLOSED Topic 004 |
| CL-03 | Firewall không tự mở category mới cho structural priors; v1 giữ 3 named categories + `UNMAPPED` governance path | `debate/002-contamination-firewall/final-resolution.md` | CONVERGED | Imported from CLOSED Topic 002 |

---

## 4. Open Issues Register

### OI-01 — Ai should own pre-lock generation lane của search space?
- **Stance**: AMEND
- **Điểm đồng ý**: Tôi giữ hai điểm đã rõ hơn sau round 1: `017` không own pre-lock ideation, và nếu tồn tại AI-assisted ideation thì nó phải dừng trước `protocol lock`; runtime vẫn thuộc offline deterministic pipeline. `Topic 018` cũng không thể mở mới trong chính round 2 này vì `debate/rules.md` §12 cấm mở topic mới sau round 1 trong cùng phiên tranh luận.
- **Điểm phản đối**: Tôi không chấp nhận suy ra từ đó rằng ownership đã khóa xong ở `006 + 015 + 017`. Repo vẫn chưa trả lời đủ câu hỏi mà Claude nêu đúng: "Who writes VDO?" `006` hiện own registry pattern, nhưng chưa own một feature-synthesis lane tối thiểu; `015` own artifact enumeration/invalidation, nhưng chưa chứng minh cơ chế sinh manifest mới.
- **Đề xuất sửa**: Giữ issue ở `OPEN`. Trong v1 của session này, chỉ khóa nguyên tắc: `006` own compiled grammar/manifest ingestion; `015` own lineage/invalidation; `017` chỉ consume compiled outputs sau lock. Câu hỏi "ai/điều gì sinh manifest mới" tiếp tục mở và không được lách bằng topic mới trong round 2.
- **Evidence**: `debate/rules.md` §12; `debate/006-feature-engine/findings-under-review.md` (X38-D-08); `debate/015-artifact-versioning/findings-under-review.md` (X38-D-14, X38-D-17); `debate/017-epistemic-search-policy/README.md`; `docs/search-space-expansion/debate/claude/claude_debate_lan_1.md`; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_1.md` (OI-01, OI-03).
- **Status after round 2**: OPEN

### OI-02 — Backbone intra-campaign nên là cell-elite coverage hay semantic prompt cross-pollination?
- **Stance**: AMEND
- **Điểm đồng ý**: Backbone của v1 vẫn là `descriptor tagging -> coverage map -> cell-elite archive -> local probes`. Điểm này bám trực tiếp `ESP-01` và được ChatGPT Pro, chính round-1 ruling của Gemini, và round-1 ruling của Codex cùng đẩy về một hướng.
- **Điểm phản đối**: Tôi bác bỏ hai cực đoan trái ngược nhau: coi prompt/domain seeding là control law của search, hoặc ngược lại dồn toàn bộ taxonomy đến tận `freeze`. `ESP-01` yêu cầu descriptor tagging ngay từ Stage 3; vì vậy taxonomy không thể xuất hiện quá muộn.
- **Đề xuất sửa**: Tách hai lớp descriptor. Lớp coarse chỉ dùng cho `cell_id` và archive diversity. Lớp richer dùng cho tagging/probing trong campaign, và richest sanitized phenotype chỉ freeze ở Stage 7. Domain-seed/prompt-cross-pollination, nếu còn giữ, chỉ là feedstock/provenance cho pre-lock manifest, không phải backbone điều khiển Stage 3-6.
- **Evidence**: `debate/017-epistemic-search-policy/findings-under-review.md` (X38-ESP-01); `debate/017-epistemic-search-policy/README.md`; `debate/006-feature-engine/findings-under-review.md` (X38-D-08); `docs/search-space-expansion/debate/gemini/gemini_debate_lan_1.md` (OI-01, OI-02); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_1.md` (OI-07, OI-08).
- **Status after round 2**: PARTIAL

### OI-03 — Surprise lane nên được thiết kế như thế nào để không nhầm novelty với value?
- **Stance**: AMEND
- **Điểm đồng ý**: Surprise chỉ là triage priority, không phải winner privilege. Tôi tiếp tục đồng ý với split `discovery gates != certification gates`, với hướng `surprise_queue -> equivalence/redundancy audit -> proof bundle -> frozen comparison set -> phenotype shadow archive`.
- **Điểm phản đối**: Tôi không chấp nhận `corr < 0.1 + IC cao` như gate chính, và cũng chưa chấp nhận khóa quá sớm minimum file inventory của `proof_bundle`. Repo hiện support requirement rằng phải có equivalence + robustness evidence, nhưng exact mandatory bundle vẫn đang phụ thuộc `003/013/015`.
- **Đề xuất sửa**: `surprise_queue` nên nằm cạnh `cell_elite_archive`, không thay archive. Chỉ cell survivors hoặc contradiction-resurrection candidates mới được vào queue. Proof bundle bắt buộc phải chứa evidence về equivalence và robustness; exact minimum contents tiếp tục mở cho upstream topics chốt.
- **Evidence**: `debate/017-epistemic-search-policy/findings-under-review.md` (X38-ESP-01, X38-ESP-02); `debate/003-protocol-engine/findings-under-review.md` (X38-D-05); `debate/013-convergence-analysis/findings-under-review.md` (X38-CA-01); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_1.md` (OI-05); `docs/search-space-expansion/debate/gemini/gemini_propone.md`.
- **Status after round 2**: PARTIAL

### OI-04 — Provenance nào là authoritative: prompt/transcript ancestry hay deterministic discovery lineage?
- **Stance**: AMEND
- **Điểm đồng ý**: Canonical lineage phải là structural/deterministic lineage của runner offline. Prompt/session ancestry chỉ có thể giữ vai trò provenance phụ trợ cho bounded ideation lane; nó không thể là replay contract chính.
- **Điểm phản đối**: Tôi cũng bác bỏ phản ứng quá tay theo hướng xem prompt/transcript là vô dụng. Nếu có pre-lock ideation lane, hash/ref của prompt hoặc session vẫn hữu ích cho human audit; chỉ là chúng không được trộn vào canonical state pack của replay semantics.
- **Đề xuất sửa**: Giữ issue ở `PARTIAL`. Tạm split `feature_lineage` và `candidate_genealogy` trong contract suy nghĩ của v1; mọi `ideation_ref`/prompt hash chỉ là supplementary provenance ngoài canonical replay contract. `015` sẽ own enumeration/invalidation; `006` cung cấp field-level inputs cho lineage.
- **Evidence**: `docs/online_vs_offline.md`; `debate/015-artifact-versioning/findings-under-review.md` (X38-D-14, X38-D-17); `debate/006-feature-engine/findings-under-review.md` (X38-D-08); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_1.md` (OI-04); `docs/search-space-expansion/debate/gemini/gemini_propone.md`.
- **Status after round 2**: PARTIAL

### OI-05 — Cross-campaign memory của v1 nên dừng ở đâu?
- **Stance**: AMEND
- **Điểm đồng ý**: Tôi giữ nguyên trần của round 1: same-dataset v1 chỉ nên build descriptor-level shadow storage; activation vượt `OBSERVED/REPLICATED_SHADOW` phải defer cho context mới thật sự. Điểm này bám `MK-17`, `ESP-03` reality check, và judgment của Topic 002 về `UNMAPPED + Tier 2 + SHADOW`.
- **Điểm phản đối**: Tôi không chấp nhận EPC full loop hay active prior ladder cho v1. Đồng thời tôi chưa thấy đủ bằng chứng để khóa ngay negative evidence là một artifact riêng biệt thay vì field bundle; phần này vẫn là storage-form question, chưa phải convergence.
- **Đề xuất sửa**: Giữ issue ở `PARTIAL`. Chốt requirement ở mức descriptor-level shadow-only contradiction/negative memory phải tồn tại; defer quyết định storage form cụ thể cho `015 + 017` khi state-pack enumeration và invalidation law chốt hơn.
- **Evidence**: `docs/design_brief.md` §3.1, §4; `debate/004-meta-knowledge/final-resolution.md` (MK-17, C3); `debate/002-contamination-firewall/final-resolution.md`; `debate/017-epistemic-search-policy/findings-under-review.md` (X38-ESP-02, X38-ESP-03, X38-ESP-04); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_1.md` (OI-06).
- **Status after round 2**: PARTIAL

### OI-06 — Breadth-expansion có được phép đi trước multiplicity/identity control không?
- **Stance**: AMEND
- **Điểm đồng ý**: Tôi giữ kết luận lõi của round 1: breadth-expansion và multiplicity/identity control là coupled design. Stage 3 scan-phase correction, equivalence relation, và minimum robustness requirement không thể bị đẩy ra ngoài sau khi breadth mechanism đã merge.
- **Điểm phản đối**: Tôi không thấy đủ bằng chứng để khóa exact law ngay ở round 2, dù là `FDR`, `Holm`, hay `cascade-is-enough`. Tôi cũng không chấp nhận freeze exact proof-bundle minimum trong khi `003`, `013`, và `015` vẫn đang mở.
- **Đề xuất sửa**: Giữ issue ở `PARTIAL`. V1 cần chốt ít nhất interface-level obligation: protocol phải khai báo explicit `scan_phase_correction_method`, `equivalence_method`, và `minimum_robustness_bundle` trước khi breadth mechanisms vượt quá local probes / bounded grammar hiện tại.
- **Evidence**: `debate/003-protocol-engine/findings-under-review.md` (X38-D-05); `debate/013-convergence-analysis/findings-under-review.md` (X38-CA-01); `debate/017-epistemic-search-policy/findings-under-review.md` (X38-ESP-01); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_1.md` (OI-03, OI-08).
- **Status after round 2**: PARTIAL

---

## 5. Per-Agent Critique

Không tạo card mới ở round 2. Mọi delta phản biện đã được hấp thụ trực tiếp vào
`OI-01` tới `OI-06` để tránh viết lại toàn bộ landscape và tránh tạo hội tụ giả.

Evidence: `docs/search-space-expansion/template/DEBATE_FORMAT.md` (round 2+ delta
rule); `debate/rules.md` §7-§9.

---

## 6. Interim Merge Direction

### 6.1 Backbone v1

Backbone v1 hiện nên được viết hẹp hơn round 1:

`bounded pre-lock ideation (optional) -> compiled manifest/operator grammar ->
descriptor tagging -> coverage map -> cell-elite archive -> local probes ->
surprise queue -> equivalence/robustness evidence -> frozen comparison set ->
shadow-only phenotype/negative-memory storage`

Điểm giữ cứng:
- AI không được trở thành runtime evaluator.
- Prompt/session refs, nếu có, chỉ là supplementary provenance.
- Không mở topic mới trong chính round 2 này để lấp khoảng trống ownership.

Evidence: `docs/online_vs_offline.md`; `debate/rules.md` §12;
`debate/017-epistemic-search-policy/findings-under-review.md` (X38-ESP-01..04).

### 6.2 Adopt ngay

| # | Artifact / Mechanism | Nguồn | Owner đề xuất |
|---|---------------------|-------|---------------|
| 1 | Compiled manifest/operator grammar ingestion contract | Codex + ChatGPT Pro + F-08 | 006 |
| 2 | Structural lineage contract (`feature_lineage`, `candidate_genealogy`, protocol/data hashes) | Codex + F-14/F-17 | 015 + 006 |
| 3 | Descriptor tagging + coverage map + cell-elite archive + local probes | ESP-01 + ChatGPT Pro | 017 + 003 |
| 4 | `surprise_queue` + equivalence/robustness gate hook + frozen comparison set hook | Codex + ChatGPT Pro | 017 + 008 + 013 + 015 |
| 5 | Shadow-only phenotype / contradiction memory contract | Codex + ChatGPT Pro + MK-17 ceiling | 017 + 015 |

### 6.3 Defer

| # | Artifact / Mechanism | Nguồn | Lý do defer |
|---|---------------------|-------|-------------|
| 1 | Topic 018 / Topic 019 umbrella | Claude + Codex round 1 | `debate/rules.md` §12 cấm mở topic mới sau round 1 trong cùng session; đây là procedural defer, không phải design verdict cuối |
| 2 | SSS như online subsystem chính thức | Claude | Quá gần online paradigm; bounded ideation lane nếu có phải compile thành artifact trước lock |
| 3 | Domain-seed / cross-domain probing như control law trung tâm | Gemini + Claude | Có giá trị như feedstock, chưa đủ bằng chứng làm backbone v1 |
| 4 | Active prior ladder vượt `OBSERVED/REPLICATED_SHADOW` | Codex + Claude | `MK-17` làm same-dataset activation inert trong v1 |
| 5 | Exact correction law (`FDR`/`Holm`/formal cascade) | 003 + 013 | Need, nhưng chưa đủ bằng chứng để khóa exact formula ở round 2 |

### 6.4 Ownership tạm

| Topic | Gánh gì |
|-------|---------|
| 006 | Compiled grammar/manifest ingestion, feature-level taxonomy, lineage inputs ở layer feature |
| 017 | Intra-campaign coverage/archive/probes/surprise semantics, shadow-only phenotype/contradiction semantics |
| 015 | Artifact enumeration, lineage schema, invalidation semantics |
| 013 | Descriptor-space convergence, information-gain / stop logic, robustness obligations interface |
| 008 | Equivalence / identity relation model giữa family, phenotype, candidate |
| 003 | Pipeline wiring sau khi upstream contracts chốt |

---

## 7. Agenda vòng sau

Chỉ tiếp tục 6 OI còn `OPEN/PARTIAL`. Giữ format phản hồi ngắn, bám đúng delta:

### OI-01
- **Stance**: AMEND
- **Điểm đồng ý**: Không mở Topic 018 trong session này; 017 không own pre-lock lane.
- **Điểm phản đối**: `006 + 015 + 017` vẫn chưa trả lời đủ "ai sinh manifest mới".
- **Đề xuất sửa**: Chốt canonical output của pre-lock lane trước, rồi mới bàn owner cuối.
- **Evidence**: `debate/rules.md` §12; `debate/006-feature-engine/findings-under-review.md`; `debate/015-artifact-versioning/findings-under-review.md`

### OI-02
- **Stance**: AMEND
- **Điểm đồng ý**: Cell-elite coverage là backbone.
- **Điểm phản đối**: Không được trì hoãn descriptor taxonomy đến tận freeze, cũng không được nâng prompt/domain seeds thành control law.
- **Đề xuất sửa**: Tách coarse cell taxonomy khỏi richer tagging/phenotype descriptors.
- **Evidence**: `debate/017-epistemic-search-policy/findings-under-review.md` (X38-ESP-01); `debate/006-feature-engine/findings-under-review.md`

### OI-03
- **Stance**: AMEND
- **Điểm đồng ý**: Surprise = triage, không phải winner privilege.
- **Điểm phản đối**: Exact minimum proof-bundle schema chưa được khóa.
- **Đề xuất sửa**: Chỉ chốt requirement ở mức equivalence + robustness evidence; để exact inventory mở cho `003/013/015`.
- **Evidence**: `debate/003-protocol-engine/findings-under-review.md`; `debate/013-convergence-analysis/findings-under-review.md`

### OI-04
- **Stance**: AMEND
- **Điểm đồng ý**: Canonical lineage là structural/deterministic lineage.
- **Điểm phản đối**: Không nên ném bỏ hoàn toàn prompt/session refs khi bounded ideation lane tồn tại.
- **Đề xuất sửa**: Chốt `supplementary provenance` bằng hash/ref, ngoài canonical replay contract.
- **Evidence**: `docs/online_vs_offline.md`; `debate/015-artifact-versioning/findings-under-review.md`

### OI-05
- **Stance**: AMEND
- **Điểm đồng ý**: Same-dataset v1 chỉ shadow-only.
- **Điểm phản đối**: Storage form của negative/contradiction memory chưa chốt.
- **Đề xuất sửa**: Chốt requirement descriptor-level shadow memory; defer storage shape.
- **Evidence**: `docs/design_brief.md`; `debate/004-meta-knowledge/final-resolution.md`; `debate/002-contamination-firewall/final-resolution.md`

### OI-06
- **Stance**: AMEND
- **Điểm đồng ý**: Breadth-expansion và multiplicity/equivalence control là coupled design.
- **Điểm phản đối**: Exact correction law vẫn chưa đủ bằng chứng để khóa.
- **Đề xuất sửa**: Yêu cầu protocol fields explicit cho correction/equivalence/robustness trước khi breadth mở rộng thêm.
- **Evidence**: `debate/003-protocol-engine/findings-under-review.md`; `debate/013-convergence-analysis/findings-under-review.md`; `debate/017-epistemic-search-policy/findings-under-review.md`

---

## 8. Change Log

| Vòng | Ngày | Agent | Tóm tắt thay đổi |
|------|------|-------|-------------------|
| 1 | 2026-03-25 | codex | Chọn `017-first backbone`, nêu 6 OI mở về owner, backbone, surprise, lineage, memory, multiplicity |
| 2 | 2026-03-26 | codex | Không thêm convergence mới; thu hẹp v1 theo hướng bounded pre-lock ideation, structural lineage canonical, cell-elite backbone, shadow-only memory, và defer procedural cho Topic 018 |

**Status Table (required by `debate/rules.md` §11)**

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| OI-01 | Owner của pre-lock generation lane | Judgment call | OPEN | — | — |
| OI-02 | Backbone intra-campaign = coverage/cell-elite hay semantic prompting | Thiếu sót | PARTIAL | — | — |
| OI-03 | Surprise lane không được nhầm novelty với value | Thiếu sót | PARTIAL | — | — |
| OI-04 | Canonical provenance = structural lineage hay prompt ancestry | Thiếu sót | PARTIAL | — | — |
| OI-05 | Cross-campaign memory của v1 dừng ở đâu | Judgment call | PARTIAL | — | — |
| OI-06 | Breadth-expansion vs multiplicity/identity control coupling | Thiếu sót | PARTIAL | — | — |
