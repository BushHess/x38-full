---
doc_type: debate_round_review
topic: search-space-expansion
round: 1
author: codex
date: 2026-03-25
status: OPEN
sources:
  - ../../request.md
  - ../gemini/gemini_propone.md
  - ./codex_propone.md
  - ../claude/claude_propone.md
  - ../chatgptpro/chatgptpro_propone.md
  - ../../../online_vs_offline.md
  - ../../../design_brief.md
  - ../../../../x38_RULES.md
  - ../../../../debate/rules.md
  - ../../../../debate/debate-index.md
  - ../../../../debate/001-campaign-model/findings-under-review.md
  - ../../../../debate/003-protocol-engine/findings-under-review.md
  - ../../../../debate/004-meta-knowledge/final-resolution.md
  - ../../../../debate/006-feature-engine/findings-under-review.md
  - ../../../../debate/007-philosophy-mission/final-resolution.md
  - ../../../../debate/008-architecture-identity/findings-under-review.md
  - ../../../../debate/013-convergence-analysis/findings-under-review.md
  - ../../../../debate/015-artifact-versioning/findings-under-review.md
  - ../../../../debate/017-epistemic-search-policy/README.md
  - ../../../../debate/017-epistemic-search-policy/findings-under-review.md
  - ../../../../debate/002-contamination-firewall/final-resolution.md
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

# Debate Round 1 — 017-First Backbone, Không Mở Pha Online Mới

## 1. Kết luận nhanh

Baseline v1 nên lấy **khung tích hợp của ChatGPT Pro** làm xương sống trong pipeline, rồi nhập thêm **discovery lineage + proof bundle + equivalence audit** từ proposal Codex (`../chatgptpro/chatgptpro_propone.md:1-18,21-35,49-63`; `./codex_propone.md:56-80,147-155,195-239`). Điểm còn sống sót từ Claude sau vòng rà là câu hỏi **ai own pre-lock generation lane**; 017 không own phần đó, nhưng Topic 018 cũng chưa được chứng minh là owner tối thiểu đúng cho v1 (`../../../../debate/017-epistemic-search-policy/README.md:25-32,43-46`; `../claude/claude_propone.md:674-705`; `./codex_propone.md:246-269`). Claude đúng khi chỉ ra x38 chưa có "discovery machine", nhưng bundle `SSS + Phase A + Topic 018` đang gộp quá nhiều quyết định vào một topic mới trước khi chứng minh được ranh giới owner tối thiểu (`../claude/claude_propone.md:553-626,667-740`). Gemini đúng khi bác bỏ sandbox online và yêu cầu provenance, nhưng proposal này quá prompt-centric và chưa đưa ra cơ chế giữ diversity trong Stage 3-6 mạnh bằng ESP-01 (`../gemini/gemini_propone.md:7-26,30-38`; `../../../../debate/017-epistemic-search-policy/findings-under-review.md:39-58`).

---

## 2. Scoreboard

| Agent | Bám yêu cầu | Bám X38 | Khả thi v1 | Sức mở search | Kỷ luật contamination | Độ rõ artifact | Verdict ngắn |
|-------|-------------|---------|------------|---------------|----------------------|----------------|--------------|
| Gemini | Trung bình | Trung bình | Tốt | Trung bình | Tốt | Trung bình | Giữ cảnh báo contamination; provenance prompt chỉ nên là audit phụ |
| Codex | Rất tốt | Tốt | Trung bình | Rất tốt | Tốt | Rất tốt | Backbone rất mạnh, nhưng đang rộng quá mức v1 |
| Claude | Rất tốt | Trung bình | Yếu | Rất tốt | Trung bình | Tốt | Nêu đúng khoảng trống, nhưng Phase A/SSS làm scope và boundary lỏng |
| ChatGPT Pro | Rất tốt | Rất tốt | Rất tốt | Tốt | Rất tốt | Tốt | Baseline v1 khả thi nhất hiện tại; cần mượn lineage/equivalence từ Codex |

**Giải thích 6 trục:**
1. **Bám yêu cầu**: giải đủ 2 tầng + gap + đề xuất bổ sung?
2. **Bám X38**: tôn trọng design brief, online/offline, Topic 017, firewall?
3. **Khả thi v1**: đưa vào draft/spec được mà không nổ scope?
4. **Sức mở search**: thực sự tăng xác suất "tai nạn tốt"?
5. **Kỷ luật contamination**: giữ Alpha-Lab là offline deterministic?
6. **Độ rõ artifact**: chỉ ra input-output-artifact-owner đủ để viết spec?

Điểm số là tổng hợp từ evidence tại §4-§5; riêng prompt provenance của Gemini được chấm như **audit adjunct**, không phải canonical lineage (`../gemini/gemini_propone.md:23-26`; `../../../online_vs_offline.md:29-43`; `../../../../debate/015-artifact-versioning/findings-under-review.md:18-54`).

---

## 3. Convergence Ledger

> Chỉ import các quyết định đã CLOSED ở topic khác; steel-man trace nằm trong
> `final-resolution.md` được cite, không được tạo mới ở đây.

| ID | Kết luận hội tụ | Basis | Status | Ghi chú |
|----|----------------|-------|--------|---------|
| CL-01 | Promise của framework vẫn là tìm candidate mạnh nhất **trong declared search space** hoặc kết luận `NO_ROBUST_IMPROVEMENT`; topic này không được lén đổi promise đó | `../../../../debate/007-philosophy-mission/final-resolution.md:46-60,81-90` | CONVERGED | Imported from CLOSED Topic 007; steel-man trace lives in that topic's closed debate |
| CL-02 | Same-dataset empirical priors vẫn shadow-only pre-freeze | `../../../../debate/004-meta-knowledge/final-resolution.md:191-193,211-223` | CONVERGED | Imported from CLOSED Topic 004; steel-man trace lives in that topic's closed debate |
| CL-03 | Firewall không tự mở category mới cho structural priors; v1 mặc định vẫn là 3 named categories + `UNMAPPED` governance path | `../../../../debate/002-contamination-firewall/final-resolution.md:35-37,79-97,101-115` | CONVERGED | Imported from CLOSED Topic 002; steel-man trace lives in that topic's closed debate |

---

## 4. Open Issues Register

> Phần chính cho debate. Mỗi issue theo format dưới đây.

### OI-01 — Ai should own pre-lock generation lane của search space?

**Các vị trí đang có**
- **Gemini**: Không mở sandbox engine; dùng domain-seed prompting + prompt ancestry, cấy vào `006/017/004` (`../gemini/gemini_propone.md:17-26,42-53`).
- **Codex**: Backbone chính nằm trong `006/017/015/013`; chỉ mở `018/019` nếu ownership hiện tại bị quá tải (`./codex_propone.md:195-258`).
- **Claude**: Mở hẳn Topic 018 + Phase A trước pipeline, gồm GFS/APE/SSS/CDAP và contract A→B (`../claude/claude_propone.md:667-740`).
- **ChatGPT Pro**: Không mở umbrella mới; đẩy Topic 017 thành P0, fold operator grammar/local probes vào `006 + 017 + 015` (`../chatgptpro/chatgptpro_propone.md:49-59,63`).

**Phán quyết vòng 1**
Round 1 giữ hai điểm cùng lúc: (1) **017 vẫn là backbone của in-pipeline search policy**, và (2) **pre-lock generation lane là owner question còn mở**. Claude thắng ở chỗ tách đúng boundary `Phase A` vs `Phase B`, nhưng chưa thắng ở bước nhảy tiếp theo rằng câu trả lời tối thiểu phải là Topic 018 bundling cả GFS/APE/SSS/CDAP (`../../../../debate/017-epistemic-search-policy/README.md:25-32,43-46`; `../claude/claude_propone.md:674-705`; `../chatgptpro/chatgptpro_propone.md:51-59`).

**Lý do**
Challenger đúng ở chỗ: 017 không own pre-pipeline generation; README của 017 tự giới hạn scope vào intra-campaign illumination, phenotype contracts, promotion ladder, và budget governor (`../../../../debate/017-epistemic-search-policy/README.md:25-32,43-46`). Điểm tôi bác bỏ không phải là boundary tách `Phase A/B`, mà là argument "đã cần owner mới thì phải là Topic 018 gộp sẵn bốn mechanisms" (`../claude/claude_propone.md:674-705`). Tự phản biện proposal Codex: phương án mở `018/019` trong `§6.2` cũng có cùng burden of proof; round này chưa đủ bằng chứng để commit owner mới, nhưng đủ bằng chứng để giữ owner question này mở thay vì gạt đi (`./codex_propone.md:246-269`).

**Phân loại**: Judgment call
**Trạng thái**: OPEN

**Điểm cần chốt vòng sau**
- Pre-lock generation lane có đủ nhỏ để split vào `006 + 015`, hay thực sự cần topic owner riêng?
- Nếu có lane pre-lock online-assisted, contract tối thiểu để nó không biến thành answer-prior channel là gì?

---

### OI-02 — Backbone intra-campaign nên là cell-elite coverage hay semantic prompt cross-pollination?

**Các vị trí đang có**
- **Gemini**: Trọng tâm là domain-seeded hypothesis synthesis, black-box hypothesis, và orthogonality filter cho "Anomaly-Alpha" (`../gemini/gemini_propone.md:17-26,34-38,46-53`).
- **Codex**: Transform grammar + descriptor-tagged frontier scan + cell-elite archive + structured mutation + scout budget (`./codex_propone.md:97-107`).
- **Claude**: GFS/APE để sinh novelty, sau đó dựa vào cell-elite archive/SDL giữ surprise sống sót (`../claude/claude_propone.md:75-143,365-421`).
- **ChatGPT Pro**: Registry lock + descriptor tagging + cell-elite archive + local-neighborhood probes + coverage floor budget (`../chatgptpro/chatgptpro_propone.md:7-19`).

**Phán quyết vòng 1**
Backbone phải là `descriptor tagging -> coverage map -> cell-elite archive -> local probes`. Prompt/domain seeding chỉ là feedstock tùy chọn, không phải luật điều khiển chính của search (`../../../../debate/017-epistemic-search-policy/findings-under-review.md:48-58,81-89`; `../../../design_brief.md:62-74`).

**Lý do**
ESP-01 đã chẩn đoán lỗi gốc của pipeline hiện tại là collapse diversity sớm vì global top-K, và đã nêu thẳng ba cơ chế cần thêm: descriptor tagging, cell-elite archive, local-neighborhood probes (`../../../../debate/017-epistemic-search-policy/findings-under-review.md:39-58`). Gemini nhìn đúng vào phần "không để AI tự do test data", nhưng argument lại trượt khỏi điểm đau của Stage 3-6: thêm domain seeds không tự tạo ra coverage obligation, per-cell survival, hay probe budget; vì vậy nó không sửa được failure mode mà ESP-01 đã nêu (`../gemini/gemini_propone.md:7-13,21-26`; `../../../../debate/017-epistemic-search-policy/findings-under-review.md:39-58`). ChatGPT Pro là proposal cân nhất ở issue này; Codex mạnh hơn về operator grammar/mutation, nhưng điều đó phải đứng trên backbone 017 chứ không thay backbone 017 (`../chatgptpro/chatgptpro_propone.md:7-19`; `./codex_propone.md:99-107`; `../../../../debate/006-feature-engine/findings-under-review.md:67-68`).

**Phân loại**: Thiếu sót
**Trạng thái**: PARTIAL

**Điểm cần chốt vòng sau**
- Descriptor taxonomy tối thiểu gồm những chiều nào để tránh vừa mù vừa nổ cell?
- Bao nhiêu survivors mỗi cell và bao nhiêu probe mỗi survivor là hợp lý cho v1?

---

### OI-03 — Surprise lane nên được thiết kế như thế nào để không nhầm novelty với value?

**Các vị trí đang có**
- **Gemini**: Gắn cờ `[Anomaly-Alpha]` theo độc lập thống kê + IC, rồi semantic recovery sau khi qua `010-clean-oos-certification` (`../gemini/gemini_propone.md:34-38`).
- **Codex**: `surprise_queue -> equivalence audit -> proof bundle -> frozen comparison set -> candidate_phenotype` (`./codex_propone.md:147-170`).
- **Claude**: Surprise Detection Layer + 3-step validation + EPC cho weak signals (`../claude/claude_propone.md:365-466,467-550`).
- **ChatGPT Pro**: Tách discovery gates khỏi certification gates, freeze comparison set, dùng evidence stack để chứng minh motif chứ không chỉ winner (`../chatgptpro/chatgptpro_propone.md:21-35`).

**Phán quyết vòng 1**
Surprise chỉ là **triage priority**, không phải đường ưu tiên vào winner lane. Core v1 nên là: triage queue, equivalence/redundancy audit, proof bundle, freeze comparison set, rồi mới distill phenotype shadow-safe (`./codex_propone.md:149-155`; `../chatgptpro/chatgptpro_propone.md:23-35`; `../../../../debate/017-epistemic-search-policy/findings-under-review.md:52-58,102-176`).

**Lý do**
Gemini đúng ở trực giác "candidate lạ cần được gắn cờ", nhưng argument quá hẹp: `corr < 0.1 + IC cao` không thay được equivalence audit, ablation, plateau, split perturbation, hay comparison set; novelty thống kê không đủ để chứng minh đây không phải clone/noise (`../gemini/gemini_propone.md:34-38`; `./codex_propone.md:149-155`; `../../../../docs/v6_v7_spec_patterns.md:284-352`). Claude đúng khi thêm preservation slots cho surprise, nhưng Step 3 yêu cầu human causal story như một phần funnel đang làm lane này phụ thuộc vào human interpretation nhiều hơn cần thiết cho v1; phần machine-verifiable phải chốt trước (`../claude/claude_propone.md:423-466`; `../../../../docs/v6_v7_spec_patterns.md:276-344`). ChatGPT Pro bổ sung đúng điểm còn thiếu: discovery gates và certification gates là hai inventory khác nhau; issue này phải bám phân tách đó (`../chatgptpro/chatgptpro_propone.md:23-27,55-56`).

**Phân loại**: Thiếu sót
**Trạng thái**: PARTIAL

**Điểm cần chốt vòng sau**
- `surprise_queue` có cần slot riêng trong cell archive hay chỉ cần queue ngoài archive?
- Proof bundle tối thiểu của surprise lane gồm những artifact nào ở v1?

---

### OI-04 — Provenance nào là authoritative: prompt/transcript ancestry hay deterministic discovery lineage?

**Các vị trí đang có**
- **Gemini**: Mandatory prompt serialization và Prompt Ancestry Tree (`../gemini/gemini_propone.md:23-26,49-50`).
- **Codex**: `discovery_lineage.json`, `operator_registry.json`, `candidate_genealogy.json` với operator chain, parenthood, roles, protocol/data hash (`./codex_propone.md:56-83`).
- **Claude**: manifests cho generated features/variants và `sss_session_log/` cho online ideation (`../claude/claude_propone.md:186-189,334-352`).
- **ChatGPT Pro**: `scan_universe.jsonl`, `protocol_freeze.json`, `mutation_log.json`, discovery artifact contract dưới Topic 015 (`../chatgptpro/chatgptpro_propone.md:7-19,51-57`).

**Phán quyết vòng 1**
Authoritative lineage phải là genealogy của operator/candidate/artifact trong runner offline. Prompt/transcript ancestry chỉ nên là **audit provenance phụ** cho ideation pre-lock, không phải canonical lineage của offline runner (`../../../online_vs_offline.md:10-25,58-66`; `../../../../debate/015-artifact-versioning/findings-under-review.md:18-54,57-110`).

**Lý do**
Gemini chạm đúng nỗi đau "VDO bị mất dấu", nhưng proposal chọn sai object để freeze: prompt là online artifact non-deterministic; Alpha-Lab cần thứ có thể replay bởi code, không phải replay bằng trí nhớ prompt (`../gemini/gemini_propone.md:11-13,23-26`; `../../../online_vs_offline.md:29-43`). Claude có cùng tension khi đưa `sss_session_log/` thành audit trail chính thức: transcripts là conversation artifact, còn 015 đang đòi canonical lineage ở layer artifact enumeration + invalidation semantics của runner (`../claude/claude_propone.md:335-352`; `../../../../debate/015-artifact-versioning/findings-under-review.md:18-54,57-110`). Điểm mạnh của Codex và ChatGPT Pro là đưa provenance về đúng layer `015`: artifact enumeration + invalidation semantics (`./codex_propone.md:67-80,228-239`; `../chatgptpro/chatgptpro_propone.md:53-57`; `../../../../debate/015-artifact-versioning/findings-under-review.md:18-54,57-110`).

**Phân loại**: Thiếu sót
**Trạng thái**: PARTIAL

**Điểm cần chốt vòng sau**
- Schema lineage tối thiểu cần những field nào để thay được "prompt bị mất"?
- Nếu có lưu external ideation refs, raw transcript có được vào canonical state pack không hay chỉ lưu hash/ref ngoài protocol?

---

### OI-05 — Cross-campaign memory của v1 nên dừng ở đâu?

**Các vị trí đang có**
- **Gemini**: Sau khi chứng minh được giá trị, semantic recovery biến "tai nạn" thành tri thức lõi/meta-knowledge (`../gemini/gemini_propone.md:35-38`).
- **Codex**: Dual archive + activation ladder; đồng thời tự giới hạn same-dataset ở shadow-only (`./codex_propone.md:152-155,248-269,345-349`).
- **Claude**: EPC lưu weak signals, maturity states, feedback loop ngược sang Phase A (`../claude/claude_propone.md:467-550,781-794,823-845`).
- **ChatGPT Pro**: Two-memory model; active logic chỉ tới sau context distance thật, còn v1 chủ yếu chốt storage/contracts (`../chatgptpro/chatgptpro_propone.md:31-35,51-59`).

**Phán quyết vòng 1**
v1 chỉ nên build **storage và shadow-safe contracts** cho phenotype/negative evidence ở descriptor level. Mọi activation vượt `OBSERVED/REPLICATED_SHADOW` phải defer; EPC-style feedback loop cũng nên defer trừ khi được chứng minh không vi phạm ceiling của MK-17 (`../../../design_brief.md:84-89`; `../../../../debate/017-epistemic-search-policy/findings-under-review.md:201-258`; `../../../../debate/017-epistemic-search-policy/README.md:139-146`).

**Lý do**
Topic 017 đã tự viết ra reality check: trên BTC/USDT same-dataset v1 thì context distance = 0, nên `ACTIVE_STRUCTURAL_PRIOR` và `DEFAULT_METHOD_RULE` là inert; README còn dự kiến v1 chỉ build storage cho `OBSERVED + REPLICATED_SHADOW`, defer activation logic (`../../../../debate/017-epistemic-search-policy/findings-under-review.md:226-258`; `../../../../debate/017-epistemic-search-policy/README.md:139-146`). ChatGPT Pro bám ceiling này chặt nhất. Tự phản biện proposal Codex: proposal của tôi thực ra đã defer activation vượt shadow-only, nhưng vẫn chưa khóa đủ rõ **v1 storage schema, invalidation rules, và local shadow retention** cho negative evidence; đó mới là phần còn mở thật sự (`./codex_propone.md:153-155,168-169,248-269`). Claude's EPC có giá trị như v2 mechanism, nhưng chưa chứng minh được feedback loop từ EPC sang SSS/CDAP/GFS trong same-dataset mode không biến thành prior lane ngụy trang (`../claude/claude_propone.md:534-549,781-794`).

**Phân loại**: Judgment call
**Trạng thái**: PARTIAL

**Điểm cần chốt vòng sau**
- Negative evidence của v1 là artifact riêng hay chỉ là field trong phenotype/proof bundle?
- EPC có được giữ dưới dạng local shadow note của campaign hay phải defer toàn bộ sang v2?

---

### OI-06 — Breadth-expansion có được phép đi trước multiplicity/identity control không?

**Các vị trí đang có**
- **Gemini**: Gần như im lặng về scan-phase multiple testing và equivalence metrics; chủ yếu dựa vào orthogonality + IC (`../gemini/gemini_propone.md:34-38`).
- **Codex**: Nêu scan-phase correction, equivalence clustering, descriptor convergence là gap cứng (`./codex_propone.md:183-191,307-325`).
- **Claude**: Có dedup/FDR/multiple-testing trong risk section nhưng không khóa nó thành backbone law (`../claude/claude_propone.md:123-129,895-900`).
- **ChatGPT Pro**: Tách discovery-gate inventory, evidence stack, pairwise diagnostics, DOF/VCBB như phần phải chuẩn hóa (`../chatgptpro/chatgptpro_propone.md:23-27,27-45,53-59`).

**Phán quyết vòng 1**
Breadth-expansion và multiplicity/identity control là **coupled design**, không phải hai workstream tách rời. Round 1 chưa đủ bằng chứng để khóa exact law, nhưng đủ bằng chứng để nói rằng v1 không nên freeze breadth mechanisms mà bỏ trống hoàn toàn correction/equivalence contract (`../../../../debate/003-protocol-engine/findings-under-review.md:53-66`; `../../../../debate/013-convergence-analysis/findings-under-review.md:32-75`; `../../../../docs/v6_v7_spec_patterns.md:276-352`).

**Lý do**
F-05 đã nêu trực diện vấn đề Stage 3 scan 50K+ configs mà chưa khóa correction law (`../../../../debate/003-protocol-engine/findings-under-review.md:60-66`). CA-01 lại chưa khóa metric để biết "candidate mới" có thực sự khác ở family/architecture/performance hay chỉ là alias khác (`../../../../debate/013-convergence-analysis/findings-under-review.md:32-63`). Vì vậy Gemini đang thiếu một khối bảo vệ bắt buộc. Claude có nhắc FDR nhưng đặt nó ở phần mitigation muộn, tức là breadth được thiết kế trước còn statistical law đi sau. Tự phản biện proposal Codex: tôi đã nêu đúng gap này nhưng chưa tách rõ ba câu hỏi riêng: scan-phase correction, equivalence threshold, và minimum evidence stack (`./codex_propone.md:183-191,307-325`; `../claude/claude_propone.md:895-900`).

**Phân loại**: Thiếu sót
**Trạng thái**: PARTIAL

**Điểm cần chốt vòng sau**
- v1 chọn FDR, Holm, hay formal cascade law cho Stage 3→4?
- `008 + 013` định nghĩa equivalence/identity threshold ở level nào là đủ cho surprise lane?
- Minimum evidence stack nào là mandatory trước khi breadth-expansion được merge vào draft?

---

## 5. Per-Agent Critique

> Mỗi agent 1 card. Phản biện tấn công argument, không phải kết luận (§4).

### 5.1 Gemini

**Luận điểm lõi**: Muốn tái tạo "tai nạn tốt" mà không phá offline, hãy để AI sinh giả thuyết chéo miền bằng prompt seeds, rồi dùng orthogonality screening và semantic recovery để phát hiện VDO mới (`../gemini/gemini_propone.md:17-38`).

**Điểm mạnh**
- Bác bỏ đúng loại giải pháp nguy hiểm nhất: sandbox online cho AI tự test/self-report; điều này bám `online_vs_offline` rất sát (`../gemini/gemini_propone.md:7-13`; `../../../online_vs_offline.md:58-66`).
- Nhìn ra đúng một lỗ hổng provenance: prompt/spec context từng làm VDO xuất hiện nhưng bị mất dấu (`../gemini/gemini_propone.md:11-13`).

**Điểm yếu — phản biện lập luận**
- **Yếu điểm 1: Prompt-domain seeding không giải quyết failure mode đã được ESP-01 nêu.** 017 chẩn đoán global top-K collapse và thiếu coverage artifacts ở Stage 3-8; Gemini không chỉ ra descriptor tagging, cell archive, hay local probes để giữ diversity sống đủ lâu (`../../../../debate/017-epistemic-search-policy/findings-under-review.md:39-58`; `../gemini/gemini_propone.md:17-26`).
- **Yếu điểm 2: `corr < 0.1 + IC cao` là novelty heuristic, không phải proof law.** Nó không thay được equivalence audit, proof bundle, hay comparison set; vì vậy argument "đánh dấu anomaly-alpha là đủ để nhận ra alpha xịn" không đứng vững (`../gemini/gemini_propone.md:34-38`; `./codex_propone.md:149-155`; `../../../../docs/v6_v7_spec_patterns.md:284-352`).
- **Yếu điểm 3: Prompt ancestry tree tấn công sai layer.** Vấn đề thật là machine-readable lineage trong runner offline; dùng prompt tree làm authoritative provenance kéo framework về online artifact dependency (`../gemini/gemini_propone.md:23-26,49-50`; `../../../online_vs_offline.md:29-43`; `../../../../debate/015-artifact-versioning/findings-under-review.md:18-54`).

**Giữ lại**: cảnh báo anti-sandbox; yêu cầu provenance không để "mất VDO" lần nữa; cho phép black-box hypothesis ở điều kiện có proof.
**Không lấy**: prompt-first backbone; anomaly-alpha heuristic như gate chính; prompt ancestry tree làm canonical lineage.

---

### 5.2 Codex

**Luận điểm lõi**: X38 cần exploration engine có lineage, diversity-preserving search, surprise triage, proof bundle, rồi phenotype distillation qua firewall (`./codex_propone.md:42-52,56-80,145-170`).

**Điểm mạnh**
- Đây là proposal rất mạnh về `artifact backbone`: lineage, genealogy, proof bundle, prior registry, equivalence audit đều được nêu thành object rõ ràng (`./codex_propone.md:67-80,149-155,228-239,284-301`).
- Bám MK-17 và firewall khá kỷ luật: activation trên same dataset dừng ở shadow-only (`./codex_propone.md:152-155,345-349`; `../../../design_brief.md:84-89`).

**Điểm yếu — phản biện lập luận**
- **Yếu điểm 1: Phần mở `018/019` chưa vượt burden of proof.** Khi 017 đã tồn tại để own search-policy gap, việc đề xuất thêm topic mới ngay vòng 1 làm authority tree nặng hơn mà chưa chứng minh interface cũ thất bại (`./codex_propone.md:246-269`; `../../../../debate/debate-index.md:139-150`; `../../../../debate/017-epistemic-search-policy/README.md:22-45`).
- **Yếu điểm 2: v1/v2 boundary chưa được siết đủ.** Dual archive, activation ladder, negative evidence registry được trình bày như backbone khá sớm, trong khi 017 tự nói v1 chủ yếu build storage và defer activation (`./codex_propone.md:152-155,248-269`; `../../../../debate/017-epistemic-search-policy/README.md:139-146`).
- **Yếu điểm 3: Multiplicity control mới dừng ở "gap list".** Argument tổng thể muốn mở breadth mạnh, nhưng lại chưa buộc scan-phase correction/equivalence metric thành prerequisite ngay trong core mechanism (`./codex_propone.md:183-191,307-325`; `../../../../debate/003-protocol-engine/findings-under-review.md:60-66`).

**Giữ lại**: discovery lineage; proof bundle; equivalence audit; phenotype distillation; surprise như triage object.
**Không lấy**: mở topic mới ở vòng này; làm negative-evidence/activation ladder trông như v1 core; để multiplicity control đứng ngoài backbone.

---

### 5.3 Claude Code

**Luận điểm lõi**: x38 hiện chỉ là verification machine; muốn tìm VDO mới phải thêm discovery machine riêng gồm GFS, APE, SSS, CDAP, SDL, EPC, và Topic 018 cho Phase A (`../claude/claude_propone.md:13-27,71-143,667-740`).

**Điểm mạnh**
- Chỉ ra đúng lỗ hổng logic "ai populate registry?" mà nhiều proposal khác lướt qua quá nhanh (`../claude/claude_propone.md:43-67`).
- Cụ thể hóa một lượng lớn mechanism search và đưa ra nhiều đường vào novelty để debate cụ thể hơn (`../claude/claude_propone.md:75-143,146-259,365-466`).

**Điểm yếu — phản biện lập luận**
- **Yếu điểm 1: Từ boundary đúng nhảy sang owner bundle quá rộng.** Claude đúng khi tách `Phase A` khỏi `Phase B`, nhưng chưa chứng minh được vì sao owner tối thiểu phải là Topic 018 gộp sẵn GFS/APE/SSS/CDAP thay vì một pre-lock contract hẹp hơn (`../claude/claude_propone.md:674-705`; `../../../../debate/017-epistemic-search-policy/README.md:25-32,43-46`).
- **Yếu điểm 2: SSS không hề "không đụng 001/002".** Một lane online chính thức dùng current registry, EPC hints, transcript logs, và human screening chạm trực tiếp vào campaign-transition law, firewall, và same-dataset shadow-only ceiling; câu "no hard dependency on 001 or 002" vì thế không đứng vững (`../claude/claude_propone.md:317-355,709-716,880-887`; `../../../design_brief.md:38-55,84-89`; `../../../../debate/001-campaign-model/findings-under-review.md:129-180`).
- **Yếu điểm 3: EPC + feedback loop vượt quá v1 ceiling.** 017 đã nói `ACTIVE` và `DEFAULT_METHOD_RULE` inert ở v1; vậy việc cho EPC mature patterns ảnh hưởng GFS/SSS/APE/CDAP quá sớm là đưa prior lane vào trước khi context distance > 0 (`../claude/claude_propone.md:526-549,792-794,842-853`; `../../../../debate/017-epistemic-search-policy/findings-under-review.md:226-258`).

**Giữ lại**: nêu rõ missing discovery machine; GFS/APE như nguồn ý tưởng; SDL trực giác preservation.
**Không lấy**: Topic 018 ở vòng này; SSS như thành phần chính thức của backbone v1; EPC feedback loop active trong same-dataset mode.

---

### 5.4 ChatGPT Pro

**Luận điểm lõi**: Đừng cố tái tạo prompt may mắn; hãy biến "tai nạn tốt" thành máy giữ diversity, đo consistency, khóa artifact, và điều này phải đi qua Topic 017/015/003 chứ không qua umbrella mới (`../chatgptpro/chatgptpro_propone.md:1-18,21-35,49-63`).

**Điểm mạnh**
- Đây là framing bám X38 rất sát: giữ execution thuần offline, dùng 017 làm search-policy backbone, tách discovery gates khỏi certification gates, và chốt artifact contract qua 015 (`../chatgptpro/chatgptpro_propone.md:23-35,51-57`; `../../../../debate/017-epistemic-search-policy/README.md:34-45`).
- Nhìn đúng tradeoff v1: giữ Topic 017 là blocker P0 thay vì mở thêm topic umbrella lớn (`../chatgptpro/chatgptpro_propone.md:51-63`; `../../../../debate/debate-index.md:68-71,139-150`).

**Điểm yếu — phản biện lập luận**
- **Yếu điểm 1: Search-space generation còn under-specified.** Proposal rất mạnh ở preservation/pruning/proof, nhưng "AI proposal sandbox" và operator grammar vẫn còn ở mức mô tả; chưa chốt lineage/generation contract đủ sâu như Codex (`../chatgptpro/chatgptpro_propone.md:13-19`; `./codex_propone.md:56-83,97-107`).
- **Yếu điểm 2: Artifact/equivalence law chưa được đóng thành contract.** Proposal nói đúng cần comparison set, pairwise matrix, evidence stack, nhưng chưa chỉ ra schema identity/equivalence/invalidation rõ như 015 + 008 + 013 đòi hỏi (`../chatgptpro/chatgptpro_propone.md:25-35,53-59`; `../../../../debate/015-artifact-versioning/findings-under-review.md:57-110`; `../../../../debate/013-convergence-analysis/findings-under-review.md:32-75`).
- **Yếu điểm 3: Dồn quá nhiều ownership vào 017 là rủi ro draftability.** Nếu không ghi ranh giới rõ với 006/015/013, proposal đúng về định hướng nhưng dễ biến 017 thành topic "ôm cả thế giới" (`../chatgptpro/chatgptpro_propone.md:51-59`; `../../../../debate/017-epistemic-search-policy/README.md:76-83,155-166`).

**Giữ lại**: 017-first backbone; cell-elite/local probes; discovery vs certification gates; comparison-set freeze; two-memory model.
**Không lấy**: để 017 absorb mọi contract mà không viết rõ interface; giữ generation contract ở mức quá mờ.

---

## 6. Interim Merge Direction

### 6.1 Backbone v1

Backbone v1 nên là: `registry/operator grammar lock -> descriptor tagging + coverage map -> cell-elite archive -> local probes/mutation batches -> proof bundle + contradiction profile -> freeze comparison set -> phenotype shadow archive`. AI có thể tham gia ở tầng **đề xuất spec/operator trước protocol lock**, nhưng output chính thức vẫn phải được compile thành universe/registry deterministic trước khi Stage 3 chạy (`../../../online_vs_offline.md:29-43`; `../../../design_brief.md:57-74`; `../../../../debate/017-epistemic-search-policy/findings-under-review.md:48-58`). Owner của pre-lock generation lane vẫn OPEN; nếu lane đó được chấp nhận ở vòng sau, nó phải kết thúc trước protocol lock và không được để AI judgment chảy vào runtime law (`../../../../debate/017-epistemic-search-policy/README.md:43-46`; `../claude/claude_propone.md:687-690`).

### 6.2 Adopt ngay

| # | Artifact / Mechanism | Nguồn | Owner đề xuất |
|---|---------------------|-------|---------------|
| 1 | Descriptor tagging + coverage map + `epistemic_delta.json` | ChatGPT Pro + ESP-01 | 017 |
| 2 | Cell-elite archive + local-neighborhood probes | ChatGPT Pro + Codex + ESP-01 | 017 + 003 |
| 3 | `discovery_lineage.json` + `candidate_genealogy.json` + operator registry | Codex + Topic 015 gap | 015 + 006 |
| 4 | Surprise queue + proof bundle + frozen comparison set | Codex + ChatGPT Pro + ESP-01/02 | 017 + 015 + 003 |
| 5 | Equivalence/redundancy audit trên common comparison domain | Codex + ChatGPT Pro | 008 + 013 |
| 6 | v1 memory ceiling: `OBSERVED/REPLICATED_SHADOW` only | ChatGPT Pro + Codex + ESP-03 | 017 + 004 + 002 |

### 6.3 Defer

| # | Artifact / Mechanism | Nguồn | Lý do defer |
|---|---------------------|-------|-------------|
| 1 | Quyết định mở Topic 018 / formal Phase A riêng | Claude | Owner question cho pre-lock generation còn OPEN; chưa đủ bằng chứng để commit bundle owner ở v1 |
| 2 | SSS như thành phần chính thức của backbone | Claude | Online/offline bridge và firewall implications chưa được chứng minh an toàn |
| 3 | CDAP | Claude + Gemini | Có giá trị brainstorm, nhưng catalog + curation cost cao, chưa phải v1 blocker |
| 4 | EPC feedback loop active sang search policy | Claude | MK-17 ceiling khiến same-dataset v1 chưa có context để activate |
| 5 | Prompt ancestry tree làm canonical lineage | Gemini | Sai layer provenance cho offline runner |
| 6 | Activation ladder vượt `REPLICATED_SHADOW` | Codex + ESP-03 | 017 đã ghi rõ v1 benefit gần như bằng 0 trên same dataset |

### 6.4 Ownership tạm

| Topic | Gánh gì |
|-------|---------|
| 006 | Operator grammar tối thiểu, feature-level taxonomy, registry contract |
| 017 | Coverage obligations, cell-elite/archive law, surprise triage semantics, v1 memory ceiling |
| 015 | Lineage/artifact enumeration, invalidation rules khi taxonomy/grammar đổi |
| 013 | Descriptor/equivalence/convergence metrics, diminishing-returns logic |
| 008 | Identity relation giữa family/architecture/phenotype/equivalence cluster |
| 003 | Stage integration: đưa các contract trên vào Stage 3-8 mà không phá freeze discipline |

---

## 7. Agenda vòng sau

Chỉ bàn các OI-* còn OPEN hoặc PARTIAL: `OI-01` đến `OI-06`.

**Format phản hồi cho agent vòng sau:**

```md
### OI-{NN}
- **Stance**: AGREE / DISAGREE / AMEND
- **Điểm đồng ý**: ...
- **Điểm phản đối**: ...
- **Đề xuất sửa**: ...
- **Evidence**: {file path hoặc finding ID}
```

---

## 8. Change Log

| Vòng | Ngày | Agent | Tóm tắt thay đổi |
|------|------|-------|-------------------|
| 1 | 2026-03-25 | codex | Round mở đầu: chốt baseline 017-first trong pipeline, giữ OPEN owner question cho pre-lock generation lane, mở 6 OI và self-critique đầy đủ 4 proposals |

### Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| OI-01 | Owner cho pre-lock generation lane | Judgment call | OPEN | — | — |
| OI-02 | Backbone diversity-preserving search inside pipeline | Thiếu sót | PARTIAL | — | — |
| OI-03 | Surprise lane = triage + proof, không phải winner shortcut | Thiếu sót | PARTIAL | — | — |
| OI-04 | Canonical lineage cho offline runner | Thiếu sót | PARTIAL | — | — |
| OI-05 | v1 memory ceiling và storage scope | Judgment call | PARTIAL | — | — |
| OI-06 | Coupling giữa breadth-expansion và multiplicity/identity control | Thiếu sót | PARTIAL | — | — |
