---
doc_type: debate_round_review
topic: search-space-expansion
round: 3
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
  - ../gemini/gemini_debate_lan_2.md
  - ./codex_debate_lan_2.md
  - ../claude/claude_debate_lan_2.md
  - ../chatgptpro/chatgptpro_debate_lan_2.md
  - ../../../online_vs_offline.md
  - ../../../design_brief.md
  - ../../../../AGENTS.md
  - ../../../../x38_RULES.md
  - ../../../../debate/rules.md
  - ../../../../debate/prompt_template.md
  - ../../../../EXECUTION_PLAN.md
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

# Debate Round 3 — Producer Contract Hẹp, Không Quay Lại Online Subsystem

## 1. Kết luận nhanh

Delta thật của round 3 là: Claude đúng ở pressure test "thiếu producer contract",
và các concession ở round 2 của Claude phải được giữ nguyên: `Topic 018`
umbrella, `SSS` first-class, và `APE` codegen không còn là live ask. Điểm còn
sống là hẹp hơn: liệu v1 có cần một deterministic `depth-1` producer law hay
không. `X38-D-08` đã cho thấy repo không ở trạng thái "registry trống"; cái còn
thiếu là contract để sinh **freezeable manifest mới** một cách audit được, không
phải lý do để kéo online session trở lại runtime (`debate/006-feature-engine/findings-under-review.md`
X38-D-08; `docs/online_vs_offline.md`; `docs/search-space-expansion/debate/claude/claude_debate_lan_2.md`
OI-03; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_2.md`
OI-01..OI-03). Tôi chấp nhận substance của `depth-1` deterministic producer,
nhưng không chấp nhận packaging của nó như một subsystem online-first, và cũng
không giả vờ rằng exact producer law đã được repo freeze. Không có
`CONVERGED` mới ở round này, vì các issue còn sống chưa đi qua đầy đủ `debate/rules.md`
§7 steel-man confirmation.

---

## 2. Scoreboard

| Agent | Bám yêu cầu | Bám X38 | Khả thi v1 | Sức mở search | Kỷ luật contamination | Độ rõ artifact | Verdict ngắn |
|-------|-------------|---------|------------|---------------|----------------------|----------------|--------------|
| Gemini | Trung bình | Tốt | Trung bình | Trung bình | Tốt | Yếu | Giữ anti-online boundary; prompt ancestry chỉ nên là provenance phụ |
| Codex | Rất tốt | Rất tốt | Tốt | Tốt | Tốt | Rất tốt | Backbone vẫn mạnh nhất sau khi bổ sung explicit producer contract |
| Claude | Tốt | Trung bình | Trung bình | Rất tốt | Trung bình | Tốt | Pressure test về producer gap là đúng; phần round-1 đã rút không nên reopen |
| ChatGPT Pro | Rất tốt | Rất tốt | Rất tốt | Tốt | Rất tốt | Rất tốt | Contract discipline tốt nhất; cần producer cụ thể hơn abstract sandbox |

Evidence: `debate/006-feature-engine/findings-under-review.md` (X38-D-08);
`debate/017-epistemic-search-policy/findings-under-review.md` (X38-ESP-01..04);
`docs/search-space-expansion/debate/claude/claude_debate_lan_2.md`;
`docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_2.md`.

---

## 3. Convergence Ledger

Không thêm `Converged` mới ở round 3. Giữ ledger cũ để tránh hội tụ giả theo
`debate/rules.md` §7-§9.

| ID | Kết luận hội tụ | Basis | Status | Ghi chú |
|----|----------------|-------|--------|---------|
| CL-01 | Promise của framework vẫn là tìm candidate mạnh nhất trong declared search space hoặc kết luận `NO_ROBUST_IMPROVEMENT` | `debate/007-philosophy-mission/final-resolution.md` | CONVERGED | Imported from CLOSED Topic 007 |
| CL-02 | Same-dataset empirical priors vẫn shadow-only pre-freeze | `debate/004-meta-knowledge/final-resolution.md` (MK-17) | CONVERGED | Imported from CLOSED Topic 004 |
| CL-03 | Firewall không tự mở category mới cho structural priors; v1 giữ `UNMAPPED + Tier 2 + SHADOW` path | `debate/002-contamination-firewall/final-resolution.md` | CONVERGED | Imported from CLOSED Topic 002 |

---

## 4. Open Issues Register

### OI-01 — Ai own pre-lock generation lane của search space?
- **Stance**: AMEND
- **Điểm đồng ý**: Claude và ChatGPT Pro đúng khi nói có một owner gap thật cho pre-lock authoring; `017` README chỉ own intra-campaign illumination / phenotype / budget, còn `006` hiện mới mô tả registry + exhaustive enumeration của features đã đăng ký (`debate/017-epistemic-search-policy/README.md`; `debate/006-feature-engine/findings-under-review.md` X38-D-08).
- **Điểm phản đối**: Tôi bác bỏ việc **reopen** hai bước nhảy đã được Claude tự rút ở round 2: quay lại `Topic 018` umbrella hoặc dựng `SSS` thành subsystem. `X38-D-08` đã giả định seeded feature families tồn tại; vì vậy argument "không có GFS thì registry tất yếu trống" vẫn là overreach. Cái repo thiếu là **producer contract cho manifest mới**, không phải bằng chứng rằng framework phải hồi sinh chat-loop (`debate/rules.md` §12; `docs/online_vs_offline.md`; `debate/006-feature-engine/findings-under-review.md` X38-D-08).
- **Đề xuất sửa**: Chốt một `pre_lock_authoring_contract` hẹp với hai producer types dùng cùng output contract: (a) **ứng viên producer hẹp nhất cho v1** = deterministic depth-1 operator enumeration trên declared primitives/operator library; (b) bounded ideation producer tùy chọn = schema-aware, results-blind proposal artifact. `006` là owner thực dụng nhất cho producer semantics + compilation; `015` own `feature_lineage` / `candidate_genealogy` / `proposal_provenance`; `017` chỉ consume frozen outputs; `003` wiring sau khi upstream close.
- **Evidence**: `debate/006-feature-engine/findings-under-review.md` (X38-D-08); `debate/015-artifact-versioning/findings-under-review.md` (X38-D-14, X38-D-17); `debate/017-epistemic-search-policy/README.md`; `docs/online_vs_offline.md`; `docs/search-space-expansion/debate/claude/claude_debate_lan_2.md` (OI-01, OI-03); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_2.md` (OI-01, OI-02, OI-03).
- **Status after round 3**: PARTIAL

### OI-02 — Backbone intra-campaign nên absorb producer tối thiểu như thế nào?
- **Stance**: AMEND
- **Điểm đồng ý**: Backbone intra-campaign vẫn là `descriptor tagging -> coverage map -> cell-elite archive -> local probes`; điểm này bám trực tiếp `X38-ESP-01` và không proposal nào round 2 bác bỏ được (`debate/017-epistemic-search-policy/findings-under-review.md` X38-ESP-01).
- **Điểm phản đối**: Tôi không chấp nhận đóng gói `depth-1` enumeration thành một subsystem tách rời với Phase-A semantics riêng. Tranh chấp còn lại không phải "Claude muốn full bundle vòng 1" nữa, mà là `depth-1` law nên được spec hóa đến đâu trong v1. Tôi cũng không chấp nhận freeze luôn các con số như 135 cells, `corr >= 0.85`, hay `Holm` ở round này; `017`, `003`, `013` vẫn để descriptor dimensions, comparison domain, và scan-phase correction mở (`debate/017-epistemic-search-policy/findings-under-review.md` X38-ESP-01; `debate/003-protocol-engine/findings-under-review.md` X38-D-05; `debate/013-convergence-analysis/findings-under-review.md` X38-CA-01).
- **Đề xuất sửa**: Treat deterministic depth-1 enumeration như **producer candidate** feeding cùng backbone, không phải backbone mới. V1 nên đọc theo chuỗi: `compiled manifest -> descriptor tagging -> coverage map -> cell-elite archive -> local probes`. Domain seeds / cross-domain hints, nếu còn giữ, chỉ sống ở supplementary provenance layer, không là control law. Mandatory hay optional vẫn là phần còn mở của issue, nhưng packaging online-first thì đã bị bác bỏ.
- **Evidence**: `debate/017-epistemic-search-policy/findings-under-review.md` (X38-ESP-01); `debate/006-feature-engine/findings-under-review.md` (X38-D-08); `debate/003-protocol-engine/findings-under-review.md` (X38-D-05); `debate/013-convergence-analysis/findings-under-review.md` (X38-CA-01); `docs/search-space-expansion/debate/claude/claude_debate_lan_2.md` (OI-03, OI-08); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_2.md` (OI-03, OI-08).
- **Status after round 3**: PARTIAL

### OI-03 — Surprise lane nên khóa ở mức nào cho v1?
- **Stance**: AMEND
- **Điểm đồng ý**: Surprise vẫn chỉ là triage priority, không phải winner privilege. Tôi đồng ý với Claude rằng SDL-style criteria hữu ích làm queue input, và đồng ý với ChatGPT Pro rằng human causal story phải đứng sau machine-verifiable proof, không đứng trong early funnel (`docs/search-space-expansion/debate/claude/claude_propone.md` §3.1; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_2.md` OI-05).
- **Điểm phản đối**: Tôi bác bỏ cả `corr < 0.1 + IC cao` của Gemini lẫn bộ threshold cụ thể của Claude như law đã khóa. Repo mới support requirement ở mức contradiction profile / comparison set / coverage evidence; exact trigger numbers chưa được finding nào freeze (`docs/search-space-expansion/debate/gemini/gemini_propone.md`; `debate/017-epistemic-search-policy/findings-under-review.md` X38-ESP-01; `debate/003-protocol-engine/findings-under-review.md` X38-D-05).
- **Đề xuất sửa**: `surprise_queue` chỉ nhận candidate từ `cell_elite_archive` hoặc `contradiction_resurrection` candidates. Minimum law của v1 là: queue input phải có ít nhất một chiều **không phải peak-score** và mọi candidate đi tiếp phải qua `equivalence_audit + proof_bundle` trước `comparison_set`. Threshold cụ thể để mở cho `017 + 013 + 003`.
- **Evidence**: `debate/017-epistemic-search-policy/findings-under-review.md` (X38-ESP-01, X38-ESP-02); `debate/003-protocol-engine/findings-under-review.md` (X38-D-05); `debate/013-convergence-analysis/findings-under-review.md` (X38-CA-01); `docs/search-space-expansion/debate/claude/claude_debate_lan_2.md` (OI-05); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_2.md` (OI-05).
- **Status after round 3**: PARTIAL

### OI-04 — Canonical provenance nên split thế nào?
- **Stance**: AMEND
- **Điểm đồng ý**: Tôi đồng ý với ChatGPT Pro và Claude round 2 rằng lineage nên split thành `feature_lineage` và `candidate_genealogy`, còn prompt/session/domain-hint refs chỉ sống ở supplementary provenance (`docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_2.md` OI-04, OI-07; `docs/search-space-expansion/debate/claude/claude_debate_lan_2.md` OI-04, OI-07).
- **Điểm phản đối**: Tôi bác bỏ cả hai cực đoan: prompt ancestry là canonical lineage, hoặc prompt/session refs hoàn toàn vô dụng. Với bounded ideation lane, `proposal_provenance` vẫn có giá trị audit và domain-hint hook; nó chỉ không được nằm trên replay path (`docs/online_vs_offline.md`; `debate/015-artifact-versioning/findings-under-review.md` X38-D-14, X38-D-17).
- **Đề xuất sửa**: `015` nên enumerate 3 artifacts riêng: `feature_lineage.jsonl`, `candidate_genealogy.jsonl`, `proposal_provenance.json`. Canonical replay phụ thuộc vào hai artifact đầu + protocol/data hashes. `proposal_provenance` có thể chứa `prompt_hash`, `transcript_ref`, `domain_hint_ref`, `author_type`, nhưng không mang invalidation semantics của replay.
- **Evidence**: `docs/online_vs_offline.md`; `debate/015-artifact-versioning/findings-under-review.md` (X38-D-14, X38-D-17); `debate/006-feature-engine/findings-under-review.md` (X38-D-08); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_2.md` (OI-04, OI-07); `docs/search-space-expansion/debate/claude/claude_debate_lan_2.md` (OI-04, OI-07); `docs/search-space-expansion/debate/gemini/gemini_propone.md`.
- **Status after round 3**: PARTIAL

### OI-05 — Cross-campaign memory của v1 nên dừng ở đâu?
- **Stance**: AMEND
- **Điểm đồng ý**: Tôi giữ nguyên ceiling: same-dataset v1 chỉ shadow-only. Descriptor-level contradiction/negative memory có ích và nên được giữ, nhưng không được biến thành answer-shaped activation (`docs/design_brief.md` §3.1, §3.3, §4; `debate/004-meta-knowledge/final-resolution.md` MK-17, C3; `debate/002-contamination-firewall/final-resolution.md`).
- **Điểm phản đối**: Tôi không chấp nhận full EPC lifecycle hay activation ladder vượt `REPLICATED_SHADOW` như core v1. Tôi cũng không chấp nhận negative memory ở dạng "đừng thử hướng X" vì nó quá gần answer prior và đụng firewall boundary (`debate/017-epistemic-search-policy/findings-under-review.md` X38-ESP-02, X38-ESP-03; `debate/002-contamination-firewall/final-resolution.md`).
- **Đề xuất sửa**: V1 chỉ commit một `contradiction_registry` descriptor-level shadow-only, populated từ `proof_bundle`, `comparison_set`, `phenotype_pack`, và `epistemic_delta`. Label này tốt hơn `negative_evidence_registry` vì nó bám `contradiction_profile` trong `ESP-01` và giảm risk hiểu sai thành answer prior. Storage shape chính xác vẫn để `015 + 017` chốt.
- **Evidence**: `docs/design_brief.md`; `debate/017-epistemic-search-policy/findings-under-review.md` (X38-ESP-01, X38-ESP-02, X38-ESP-03); `debate/004-meta-knowledge/final-resolution.md` (MK-17, C3); `debate/002-contamination-firewall/final-resolution.md`; `docs/search-space-expansion/debate/claude/claude_debate_lan_2.md` (OI-06); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_2.md` (OI-06).
- **Status after round 3**: PARTIAL

### OI-06 — Breadth-expansion có được phép đi trước multiplicity / identity control không?
- **Stance**: AMEND
- **Điểm đồng ý**: Tôi đồng ý với `NEW-01` của ChatGPT Pro và pressure test từ round 1/2 rằng breadth-expansion là coupled design với common comparison domain, identity vocabulary, scan-phase correction, và minimum robustness bundle (`debate/003-protocol-engine/findings-under-review.md` X38-D-05; `debate/013-convergence-analysis/findings-under-review.md` X38-CA-01).
- **Điểm phản đối**: Tôi không chấp nhận đóng ngay exact law như `Holm`, `corr >= 0.85`, hay bộ cell dimensions cố định, vì chính `ESP-01`, `F-05`, `CA-01` còn ghi chúng là câu hỏi mở. Freeze các con số này bây giờ sẽ overreach evidence base (`debate/017-epistemic-search-policy/findings-under-review.md` X38-ESP-01; `debate/003-protocol-engine/findings-under-review.md` X38-D-05; `debate/013-convergence-analysis/findings-under-review.md` X38-CA-01).
- **Đề xuất sửa**: Giữ issue ở `OPEN`, nhưng thu hẹp câu hỏi còn lại: trước khi bật producer breadth rộng hơn registry hiện hữu, v1 spec phải freeze một interface bundle gồm `descriptor_core_v1`, `common_comparison_domain`, `identity_vocabulary`, `scan_phase_correction_method`, và `minimum_robustness_bundle`. Đây là contract blocker thực sự; exact formulas có thể xuống spec downstream.
- **Evidence**: `debate/017-epistemic-search-policy/findings-under-review.md` (X38-ESP-01); `debate/003-protocol-engine/findings-under-review.md` (X38-D-05); `debate/013-convergence-analysis/findings-under-review.md` (X38-CA-01); `debate/008-architecture-identity/findings-under-review.md` (X38-D-13); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_2.md` (NEW-01, OI-08); `docs/search-space-expansion/debate/claude/claude_debate_lan_2.md` (OI-08).
- **Status after round 3**: OPEN

---

## 5. Per-Agent Critique

### 5.1 Gemini

**Luận điểm lõi**: offline-first + domain-seed prompting + prompt ancestry.

**Điểm mạnh**
- Anti-online boundary của Gemini vẫn hữu ích để chặn SSS-style subsystem (`docs/online_vs_offline.md`; `docs/search-space-expansion/debate/gemini/gemini_propone.md`).
- `semantic recovery` vẫn có giá trị như lớp explanatory note sau proof, không phải gate (`docs/search-space-expansion/debate/gemini/gemini_propone.md`).

**Điểm yếu — phản biện lập luận**
- **Yếu điểm 1: attack đúng rủi ro, nhưng attack sai object.**
  Prompt ancestry không thay canonical replay semantics; offline state transfer là machine-enforced artifact lineage, không phải conversation memory (`docs/online_vs_offline.md`; `debate/015-artifact-versioning/findings-under-review.md` X38-D-14, X38-D-17).

**Giữ lại**: `domain_hint_ref` như supplementary provenance; semantic recovery sau proof.
**Không lấy**: prompt ancestry tree như canonical lineage; `corr + IC` như recognition law chính.

### 5.2 Codex

**Luận điểm lõi**: lineage + coverage/archive/proof + shadow-only distillation.

**Điểm mạnh**
- Contract backbone vẫn bám repo tốt nhất: lineage, cell-elite, proof bundle, phenotype/distillation (`docs/search-space-expansion/debate/codex/codex_propone.md`; `debate/017-epistemic-search-policy/findings-under-review.md` X38-ESP-01, X38-ESP-02).

**Điểm yếu — phản biện lập luận**
- **Yếu điểm 1: round 2 của chính tôi under-specify producer contract.**
  Câu "AI freedom trước protocol lock" là đúng hướng, nhưng chưa đủ object-level để trả lời Claude's pressure test. Round 3 sửa điểm này bằng `pre_lock_authoring_contract`, không bằng topic mới (`docs/search-space-expansion/debate/codex/codex_debate_lan_2.md` OI-01, OI-02; `debate/006-feature-engine/findings-under-review.md` X38-D-08).

**Giữ lại**: lineage, equivalence/proof, contradiction memory, shadow-only ceiling.
**Không lấy**: khả năng mở `018/019` như hướng ưu tiên trong session hiện tại.

### 5.3 Claude

**Luận điểm lõi**: backbone hiện tại chưa trả lời "ai/cái gì tạo feature mới".

**Điểm mạnh**
- Pressure test của Claude là đúng target nhất trong round 3: nếu không formalize producer contract, search-space expansion chỉ là archive/pruning tốt hơn cho declared space cũ (`docs/search-space-expansion/debate/claude/claude_debate_lan_2.md` OI-03).

**Điểm yếu — phản biện lập luận**
- **Yếu điểm 1: substance còn sống, packaging cũ đã bị rút và không nên lôi lại.**
  Round 2 của Claude đã tự rút `Topic 018` umbrella, `SSS` first-class, và `APE` codegen. Phần còn tranh luận là hẹp hơn: `depth-1` producer law và bounded ideation lane nên spec hóa thế nào. Ở đó, điểm tôi bác là việc biến `depth-1` producer thành subsystem có semantics riêng thay vì một producer contract cùng họ với compiled manifest (`docs/search-space-expansion/debate/claude/claude_debate_lan_2.md`; `docs/online_vs_offline.md`).

**Giữ lại**: deterministic depth-1 enumeration như producer candidate; simplified SDL criteria như queue inputs.
**Không lấy**: reopen `SSS` first-class, `APE` codegen, `Topic 018` umbrella.

### 5.4 ChatGPT Pro

**Luận điểm lõi**: build machine giữ diversity, motif consistency, artifact contracts.

**Điểm mạnh**
- Gate split, critical-path realism, và contract thinking của ChatGPT Pro vẫn là co-baseline mạnh nhất (`docs/search-space-expansion/debate/chatgptpro/chatgptpro_propone.md`; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_2.md`).

**Điểm yếu — phản biện lập luận**
- **Yếu điểm 1: producer vẫn quá abstract nếu chỉ dừng ở sandbox/spec.**
  Round 2 của ChatGPT Pro đã thu hẹp câu hỏi bằng `depth-1 grammar enumeration`, nhưng round 1 và proposal gốc còn để trống bước compile từ proposal thành feature-producing contract (`docs/search-space-expansion/debate/chatgptpro/chatgptpro_propone.md`; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_1.md`; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_2.md` OI-03).

**Giữ lại**: bounded ideation contract, gate split, consistency motif, ownership split.
**Không lấy**: exact thresholds/laws ở round này khi `003/013/017` còn mở.

---

## 6. Interim Merge Direction

### 6.1 Backbone v1

Backbone v1 nên được đọc lại như sau:

`optional bounded ideation (results-blind) -> deterministic depth-1 compiled enumeration -> protocol lock -> descriptor tagging -> coverage map -> cell-elite archive -> local probes -> surprise_queue -> equivalence_audit -> proof_bundle -> comparison_set + phenotype_pack + contradiction_registry (shadow-only)`

Điểm giữ cứng:
- AI không được trở thành runtime evaluator.
- `proposal_provenance` không nằm trên replay path.
- Breadth producer mới phải đi cùng interface bundle cho identity/equivalence/correction.

### 6.2 Adopt ngay

| # | Artifact / Mechanism | Nguồn | Owner đề xuất |
|---|---------------------|-------|---------------|
| 1 | `pre_lock_authoring_contract` với producer contract chung cho compiled enumeration + bounded ideation | Claude pressure test + ChatGPT Pro contract discipline + Codex gap G1/G9 | 006 + 015 |
| 2 | `feature_lineage.jsonl` + `candidate_genealogy.jsonl` + `proposal_provenance.json` | Codex + ChatGPT Pro + OI-04 narrowing | 015 + 006 |
| 3 | Deterministic depth-1 operator enumeration feeding manifest trước lock | Claude substance narrowed by Codex | 006 |
| 4 | `descriptor_core_v1` + `coverage_map` + `cell_elite_archive` + `local_probes` | X38-ESP-01 + Codex + ChatGPT Pro | 017 + 006 + 003 |
| 5 | `surprise_queue` + `equivalence_audit` + `proof_bundle` + `comparison_set` | Codex + Claude SDL slice + ChatGPT Pro | 017 + 013 + 015 |
| 6 | `contradiction_registry` descriptor-level shadow-only tied to phenotype/proof artifacts | Codex + ChatGPT Pro, bounded by MK-17 + Topic 002 | 017 + 015 |

### 6.3 Defer

| # | Artifact / Mechanism | Nguồn | Lý do defer |
|---|---------------------|-------|-------------|
| 1 | Topic 018 / 019 umbrella | Earlier Claude + earlier Codex option | `debate/rules.md` §12 + current owner split still viable; round 2 của Claude đã rút hướng này |
| 2 | SSS first-class subsystem | Earlier Claude | Quá gần online paradigm; round 2 của Claude đã rút hướng này |
| 3 | GFS depth 2/3, CDAP/domain catalog | Claude + Gemini | Producer breadth vượt xa contract maturity hiện tại |
| 4 | APE code generation | Earlier Claude | Self-critique đã cho thấy correctness/scale risk quá cao cho v1; round 2 đã rút |
| 5 | Exact cell dimensions, equivalence thresholds, correction formula | Claude + ChatGPT Pro | `017/003/013` vẫn chưa freeze exact law |
| 6 | Activation ladder vượt `REPLICATED_SHADOW` | Codex + Claude | `MK-17` + `C3` làm v1 same-dataset activation inert |

### 6.4 Ownership tạm

| Topic | Gánh gì |
|-------|---------|
| 006 | Producer semantics, operator library, deterministic depth-1 enumeration, feature-level taxonomy, compile-to-manifest |
| 015 | Lineage/provenance artifacts, artifact enumeration, invalidation semantics khi producer/taxonomy đổi |
| 017 | Coverage obligations, archive/probe law, surprise semantics, phenotype/contradiction shadow storage, budget governor |
| 013 | Common comparison domain, convergence/diminishing-returns hooks, robustness obligations interface |
| 008 | Identity vocabulary boundary (`same feature/candidate/phenotype/system`) khi spec hóa chi tiết |
| 003 | Stage insertion points và gating sau khi 006/015/017/013 close |

---

## 7. Agenda vòng sau

Chỉ tiếp tục các OI còn `OPEN/PARTIAL`.

### OI-01
- **Stance**: AMEND
- **Điểm đồng ý**: Pre-lock producer gap là có thật; 017 không own nó.
- **Điểm phản đối**: Owner gap không tự suy ra Topic 018 hay SSS.
- **Đề xuất sửa**: Chốt `pre_lock_authoring_contract` và producer types trước khi bàn topic mới.
- **Evidence**: `debate/006-feature-engine/findings-under-review.md`; `debate/017-epistemic-search-policy/README.md`; `debate/rules.md` §12

### OI-02
- **Stance**: AMEND
- **Điểm đồng ý**: Depth-1 deterministic producer là substance nên giữ.
- **Điểm phản đối**: Không freeze luôn subsystem semantics hay exact cell/correction numbers.
- **Đề xuất sửa**: Treat depth-1 enumeration như producer feeding `ESP-01` backbone.
- **Evidence**: `debate/017-epistemic-search-policy/findings-under-review.md` (X38-ESP-01); `debate/003-protocol-engine/findings-under-review.md`

### OI-03
- **Stance**: AMEND
- **Điểm đồng ý**: Surprise = triage, không phải winner privilege.
- **Điểm phản đối**: Threshold cụ thể của SDL hoặc IC-screen chưa đủ source support.
- **Đề xuất sửa**: Chốt law ở mức `queue input -> equivalence audit -> proof bundle -> comparison set`.
- **Evidence**: `debate/017-epistemic-search-policy/findings-under-review.md`; `debate/013-convergence-analysis/findings-under-review.md`

### OI-04
- **Stance**: AMEND
- **Điểm đồng ý**: Split lineage/provenance đang có cùng hướng lớn giữa các bên.
- **Điểm phản đối**: Prompt/session refs không được lên replay path.
- **Đề xuất sửa**: 3-artifact split với `proposal_provenance` là supplementary only.
- **Evidence**: `docs/online_vs_offline.md`; `debate/015-artifact-versioning/findings-under-review.md`

### OI-05
- **Stance**: AMEND
- **Điểm đồng ý**: Shadow-only contradiction memory nên tồn tại ở v1.
- **Điểm phản đối**: EPC/active ladder vượt shadow-only chưa có v1 value.
- **Đề xuất sửa**: Chốt descriptor-level `contradiction_registry`, để storage shape mở cho 015/017.
- **Evidence**: `docs/design_brief.md`; `debate/004-meta-knowledge/final-resolution.md`; `debate/002-contamination-firewall/final-resolution.md`

### OI-06
- **Stance**: AMEND
- **Điểm đồng ý**: Breadth-expansion và multiplicity/equivalence control là coupled design.
- **Điểm phản đối**: Exact thresholds/formulas hiện vẫn overreach evidence.
- **Đề xuất sửa**: Chốt interface bundle bắt buộc trước khi bật breadth producer rộng hơn.
- **Evidence**: `debate/017-epistemic-search-policy/findings-under-review.md`; `debate/003-protocol-engine/findings-under-review.md`; `debate/013-convergence-analysis/findings-under-review.md`

---

## 8. Change Log

| Vòng | Ngày | Agent | Tóm tắt thay đổi |
|------|------|-------|-------------------|
| 1 | 2026-03-25 | codex | Chọn `017-first backbone`, nêu 6 OI mở về owner, backbone, surprise, lineage, memory, multiplicity |
| 2 | 2026-03-26 | codex | Thu hẹp v1 theo bounded pre-lock ideation, structural lineage canonical, cell-elite backbone, shadow-only memory |
| 3 | 2026-03-26 | codex | Chấp nhận producer-gap pressure test nhưng bác bỏ online-first packaging; đề xuất `pre_lock_authoring_contract`, narrow deterministic depth-1 producer, 3-artifact lineage split, và giữ multiplicity/equivalence bundle ở trạng thái OPEN |

**Status Table (required by `debate/rules.md` §11)**

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| OI-01 | Owner của pre-lock generation lane | Judgment call | PARTIAL | — | — |
| OI-02 | Backbone intra-campaign + producer integration | Thiếu sót | PARTIAL | — | — |
| OI-03 | Surprise lane không được nhầm novelty với value | Thiếu sót | PARTIAL | — | — |
| OI-04 | Canonical provenance = structural lineage, prompt refs = provenance phụ | Thiếu sót | PARTIAL | — | — |
| OI-05 | Cross-campaign memory của v1 dừng ở shadow-only contradiction storage | Judgment call | PARTIAL | — | — |
| OI-06 | Breadth-expansion vs multiplicity/identity/correction coupling | Thiếu sót | OPEN | — | — |
