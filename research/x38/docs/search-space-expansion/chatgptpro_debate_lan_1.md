---
doc_type: debate_round_review
topic: search-space-expansion
round: 1
author: chatgptpro
date: 2026-03-25
status: OPEN
sources:
  - ./request.md
  - ./gemini_propone.md
  - ./codex_propone.md
  - ./claude_propone.md
  - ./chatgptpro_propone.md
  - ../design_brief.md
  - ../../EXECUTION_PLAN.md
  - ../online_vs_offline.md
  - ../../debate/017-epistemic-search-policy/findings-under-review.md
  - ../validation_mapping_table.md
  - ../v6_v7_spec_patterns.md
  - ../../../STRATEGY_STATUS_MATRIX.md
tracking_rules:
  - Convergence Ledger là nguồn chân lý cho các điểm đã chốt ở vòng hiện tại.
  - Các vòng sau chỉ được bàn các mục trong Open Issues Register, trừ khi tạo REOPEN-* với bằng chứng mới.
  - Không được đổi ID cũ, không được đánh số lại, không được viết lại toàn bộ landscape ở mỗi vòng.
  - Ý tưởng mới không map được vào issue cũ phải tạo NEW-* và giải thích vì sao issue hiện tại không bao phủ đủ.
reopen_rule:
  - Có bằng chứng mới từ repo/spec khiến kết luận cũ sai hoặc thiếu.
  - Có xung đột kiến trúc lộ ra khi draft spec/implementation.
  - Có phát hiện contamination/gov risk mà vòng trước chưa nhìn thấy.
status_legend:
  - CONVERGED: đã đủ chắc để không bàn lại ở vòng sau.
  - PARTIAL: cùng hướng lớn nhưng chi tiết chưa khóa.
  - OPEN: còn tranh chấp thực chất.
  - DEFER: ý tưởng có giá trị nhưng không nên là trọng tâm v1.
---

# Debate Round 1 — Đánh giá phản biện và khung chuẩn cho các vòng sau

## Kết luận nhanh

Nếu buộc phải chọn **một** bản làm baseline để merge tiếp, tôi chọn **`codex_propone.md`**.

Nếu buộc phải chọn **hai** nguồn neo chính cho hướng đi tiếp theo, tôi chọn:
1. **Codex** làm backbone kiến trúc discovery.
2. **ChatGPT Pro** làm backbone về guardrail, artifact contract, gate split và bám sát critical path của X38.

Đánh giá ngắn gọn từng bên:
- **Gemini**: có 2 hạt nhân tốt đáng giữ, nhưng quá mỏng để làm backbone.
- **Codex**: cân bằng nhất, bám bài toán tốt, có xương sống rõ.
- **Claude**: nhiều ý tưởng mạnh, nhưng đang overbuild và kéo framework đi gần lại online hơn mức cần thiết.
- **ChatGPT Pro**: thực dụng, bám repo tốt, nhưng cần mượn thêm lineage/equivalence/negative-memory từ Codex để hoàn chỉnh.

## Cách dùng file này cho các vòng sau

1. Đọc **Convergence Ledger** trước. Những mục ở đây xem như đã khóa tạm thời.
2. Chỉ phản biện các mục trong **Open Issues Register**.
3. Nếu muốn lật lại một điểm đã khóa, phải tạo `REOPEN-*` kèm bằng chứng mới từ repo hoặc xung đột kiến trúc rõ ràng.
4. Không được viết lại toàn bộ tranh luận từ đầu. Vòng sau chỉ cập nhật:
   - `Kết luận nhanh`
   - `Scoreboard`
   - `Open Issues Register`
   - `Interim Merge Direction`
   - `Change Log`
5. Khi một issue đã hội tụ, chuyển nó sang **Convergence Ledger** và xóa khỏi agenda vòng sau.

---

## 1) Rubric đánh giá

Tôi chấm trên 6 trục:
1. **Bám yêu cầu gốc**: có giải được đủ 2 tầng + gap + đề xuất bổ sung hay không.
2. **Bám X38 hiện tại**: có tôn trọng design brief, online/offline split, Topic 017, critical path, firewall hay không.
3. **Khả thi cho v1**: có thể đưa vào draft/spec gần hạn mà không làm nổ scope hay không.
4. **Sức mở search space**: có thực sự làm tăng xác suất sinh ra “tai nạn tốt” hay chỉ cải thiện phán xử.
5. **Kỷ luật contamination / governance**: có giữ được Alpha-Lab là offline deterministic system hay không.
6. **Độ rõ artifact / ownership**: có chỉ ra input-output-artifact-owner đủ để chuyển thành spec hay không.

### Scoreboard

| Agent | Bám yêu cầu | Bám X38 hiện tại | Khả thi v1 | Sức mở search space | Kỷ luật contamination | Độ rõ artifact/owner | Verdict ngắn |
|---|---|---|---|---|---|---|---|
| Gemini | Trung bình | Tốt | Trung bình | Trung bình | Rất tốt | Yếu | Giữ một số ý, không dùng làm backbone |
| Codex | Rất tốt | Rất tốt | Tốt | Rất tốt | Tốt | Rất tốt | **Baseline tốt nhất** |
| Claude | Tốt | Trung bình | Trung bình | Rất tốt | Trung bình | Tốt | Kho ý tưởng mạnh, nhưng overbuild |
| ChatGPT Pro | Rất tốt | Rất tốt | Tốt | Tốt | Rất tốt | Rất tốt | **Co-baseline về guardrail** |

---

## 2) Convergence Ledger

> Chỉ các điểm thật sự đã đủ chắc mới được đưa vào đây. Vòng sau không bàn lại trừ khi có `REOPEN-*`.

| ID | Kết luận hội tụ | Basis | Status | Ghi chú cho vòng sau |
|---|---|---|---|---|
| CL-01 | X38 hiện mạnh ở **verification/validation**, nhưng còn thiếu **discovery/search-space expansion**. | 4/4 proposal + repo context | CONVERGED | Không cần bàn lại chẩn đoán nền. Chỉ bàn cách sửa. |
| CL-02 | Bài toán phải tách thành **Tầng 1: exploration** và **Tầng 2: recognition/systematization**. | Yêu cầu gốc + 4/4 proposal | CONVERGED | Các vòng sau chỉ tranh luận cơ chế cụ thể cho từng tầng. |
| CL-03 | Sau khi search space/manifest được khóa, execution chính thức phải là **deterministic offline pipeline**; AI không được trở thành evaluator trong runtime. | Repo invariant + 4/4 proposal theo các mức khác nhau | CONVERGED | Mọi ý tưởng mới phải tuân invariant này. |
| CL-04 | Discovery phải để lại **artifact machine-readable**; không thể dựa vào trí nhớ prompt hay transcript. | 4/4 proposal + repo gaps | CONVERGED | Tranh luận tiếp chỉ còn ở chỗ “artifact nào là canonical”. |
| CL-05 | Surprise không được bị bóp chết bởi logic **global top-K / peak-score only**; cần một lane để giữ ứng viên lạ đủ lâu. | Topic 017 + Codex + Claude + ChatGPT Pro + Gemini (orthogonality screen) | CONVERGED | Vòng sau chỉ khóa thiết kế lane, không bàn lại nhu cầu. |
| CL-06 | **Discovery gates** và **certification / deployment gates** là hai hệ khác nhau, không được trộn. | Repo constraint mạnh (F-41, status matrix) + Codex/ChatGPT Pro | CONVERGED | Vòng sau bàn inventory cụ thể, không bàn lại nguyên tắc. |
| CL-07 | Freeze nên giữ **comparison set + coverage/phenotype evidence**, không chỉ một winner đơn lẻ. | Topic 017 + Codex + ChatGPT Pro; không có phản đề mạnh | CONVERGED | Vòng sau bàn schema và scope, không bàn lại principle. |
| CL-08 | Same-dataset learned priors phải ở **shadow-only**; không được kích hoạt thành answer prior trước context mới thật sự. | Design brief / Topic 017 invariant + Codex + Claude + ChatGPT Pro | CONVERGED | Mọi design memory/feedback loop phải kiểm against rule này. |

---

## 3) Open Issues Register

> Đây là phần chính cho các vòng sau. Chỉ bàn các mục ở đây.

### OI-01 — Có nên mở Topic mới kiểu `018-search-space-expansion`, hay fold vào các topic hiện có?

**Các vị trí đang có**
- **Gemini**: không cần topic mới; bổ sung vào `006`, `017`, `004`.
- **Codex**: có hai đường; ưu tiên có thể mở rộng topic hiện có, nhưng nếu ownership quá chật thì mở `018/019` riêng.
- **Claude**: nên mở hẳn **Topic 018** để sở hữu Phase A.
- **ChatGPT Pro**: không nên mở topic umbrella mới quá sớm; nên ép `017 + 006 + 015 (+013/008 khi cần)` gánh trước.

**Phán quyết vòng 1**
- Tôi **không ủng hộ** mở ngay một Topic 018 kiểu umbrella ở thời điểm này.
- Tôi **cũng không phủ nhận** rằng Claude đã nhìn đúng một thiếu hụt thật: X38 chưa có câu trả lời rõ cho “ai/điều gì sẽ khai báo search space mới”.
- Hướng phù hợp nhất lúc này là **đi theo đường của Codex nhưng nghiêng về ChatGPT Pro**:
  - v1: nhốt trong topic hiện có (`006`, `017`, `015`, `013`, `008`, `003` khi đến lượt).
  - chỉ mở topic mới nếu sau 1-2 vòng nữa ownership thật sự bị tràn và gây mâu thuẫn liên topic.

**Lý do**
1. `017` đang nằm trên critical path trước `003`; mở thêm umbrella topic bây giờ rất dễ làm nổ scope và làm chậm protocol topic.
2. Bản chất thứ đang thiếu hiện tại là **artifact contract + grammar + discovery policy + gate inventory**, chưa phải một “pillar” kiến trúc độc lập đã đủ chín.
3. Nếu mở 018 quá sớm, nguy cơ cao là ta hợp thức hóa một subsystem lớn trước khi chốt được rule nền ở `017/015/006`.

**Trạng thái**: OPEN

**Điểm cần chốt ở vòng sau**
- Điều kiện nào đủ để nói “topic hiện có không gánh nổi, phải tách topic mới”? 
- Nếu tách, topic mới nên hẹp kiểu `operator-grammar + lineage`, hay rộng kiểu `Phase A`?

---

### OI-02 — Có nên có một lane “creative AI session” rõ ràng như Claude SSS, hay chỉ cho AI tham gia ở mức spec/manifest?

**Các vị trí đang có**
- **Gemini**: chống mạnh mô hình sandbox online; ideation nên ở text/spec, không phải AI tự test.
- **Codex**: AI freedom ở lớp khai báo trước protocol lock; sau khi manifest đã khóa thì execution phải deterministic.
- **Claude**: có thể có **SSS** như một online Phase A rõ ràng, có transcript, có prompt template, có screening.
- **ChatGPT Pro**: cho AI tự do ở tầng spec/module/operator, nhưng không cho AI thành một phần của execution hay verdict pipeline.

**Phán quyết vòng 1**
- Tôi **bác bỏ** mô hình “AI creative session” như **first-class subsystem** của v1 theo đúng hình hài SSS hiện tại.
- Tôi **chấp nhận** một dạng **bounded ideation lane** với rule rất cứng:
  1. output canonical phải là `proposal_spec/manifest/operator pack`, không phải transcript;
  2. AI không có quyền evaluate, select, rank, hay tác động trực tiếp vào verdict;
  3. AI không được nhìn prior answer-level results trên cùng dataset;
  4. mọi thứ phải compile thành machine-readable artifact trước khi vào pipeline.

**Lý do**
1. `online_vs_offline.md` đã nói rất rõ: online và offline là hai paradigm khác nhau; Alpha-Lab không nên nhập nhằng execution với AI conversation.
2. Cái cần giữ từ “tai nạn VDO” là **surface area cho ideation**, không phải lôi hẳn chat session trở lại làm thành phần kiến trúc chính.
3. Claude đúng ở chỗ cần trả lời “Who writes VDO?”, nhưng cách đưa SSS thành explicit online phase ngay từ v1 là **quá gần với paradigm cũ**.

**Trạng thái**: OPEN

**Điểm cần chốt ở vòng sau**
- Canonical output của bounded ideation lane là gì?
- Prompt/session log có phải artifact bắt buộc hay chỉ là provenance phụ?

---

### OI-03 — Minimum viable discovery engine cho v1 nên gồm những gì?

**Các vị trí đang có**
- **Gemini**: domain-seed prompting + black-box hypothesis + orthogonality screen.
- **Codex**: discovery lineage + transform/operator grammar + coverage map + cell-elites + mutation + surprise triage + proof bundle.
- **Claude**: GFS + APE + SSS + SDL ngay từ v1; CDAP/EPC defer v2.
- **ChatGPT Pro**: 017-centered package gồm descriptor coverage, cell-elite, local probes, contradiction search, gate split, artifact contract, evidence stack.

**Phán quyết vòng 1**
Tôi đề xuất **v1 = Codex + ChatGPT Pro**, với phạm vi tối thiểu như sau:
1. `discovery_lineage.json` / `operator_registry.json` / `candidate_genealogy.json`
2. descriptor taxonomy đủ dùng + `coverage_map`
3. `cell_elite_archive` thay global top-K
4. bounded `operator grammar` + `local-neighborhood probes`
5. `surprise_queue` / equivalence audit / proof bundle
6. freeze comparison set + phenotype pack + `epistemic_delta.json`
7. shadow-only prior / contradiction / negative-evidence registry tối thiểu

**Không nên là core v1**
- CDAP/domain-seed engine
- full EPC lifecycle
- GFS depth 2/3 ở quy mô lớn
- SSS như subsystem online độc lập

**Lý do**
- Gemini **quá nhẹ**, chưa đủ engine.
- Claude **quá rộng**, dễ nổ compute và governance trước khi chốt được rule nền.
- Codex và ChatGPT Pro ghép lại cho ra một v1 vừa thực dụng vừa đủ discovery-native.

**Trạng thái**: OPEN

**Điểm cần chốt ở vòng sau**
- v1 có cần GFS depth-1 không, hay grammar+local probes là đủ?
- negative-evidence registry ở v1 nên tối thiểu đến đâu để không quá nặng?

---

### OI-04 — Canonical lineage nên là gì? Prompt ancestry có vai trò gì?

**Các vị trí đang có**
- **Gemini**: prompt ancestry / semantic context phải được version hóa; có `Prompt Ancestry Tree`.
- **Codex**: canonical lineage là machine-readable operator/candidate genealogy.
- **Claude**: session logs/transcripts/manifests đều được giữ lại.
- **ChatGPT Pro**: trọng tâm là frozen spec / artifact contract / phenotype pack; prompt không phải trung tâm.

**Phán quyết vòng 1**
- **Canonical lineage** phải là **machine-readable structural lineage**, không phải prompt text.
- Tôi xem prompt/session ancestry là **provenance phụ trợ**, chỉ dùng khi bounded ideation lane tồn tại.
- Một prompt rất hữu ích cho audit con người, nhưng **không đủ** để replay, dedup, equivalence audit, invalidation hay distillation.

**Kết luận tạm**
- **Bắt buộc**: raw channel, operator chain, parent candidate(s), role assignment, threshold mode, timeframe binding, protocol hash, data snapshot hash.
- **Tùy chọn**: prompt hash, transcript reference, domain hint, AI model metadata.

**Trạng thái**: OPEN

**Điểm cần chốt ở vòng sau**
- Có cần tách `feature_lineage` và `candidate_lineage` riêng không?
- Prompt hash có nên nằm trong canonical schema hay chỉ trong supplementary provenance?

---

### OI-05 — Recognition stack chuẩn nên gồm những bước nào, và human đứng ở đâu?

**Các vị trí đang có**
- **Gemini**: orthogonality + IC anomaly flag, sau đó semantic recovery.
- **Codex**: surprise triage → equivalence audit → proof bundle → phenotype distillation → activation ladder.
- **Claude**: SDL multi-criteria → 3-step validation → EPC/human checkpoint.
- **ChatGPT Pro**: gate split + evidence stack + consistency motif + convergence + two-memory model.

**Phán quyết vòng 1**
Tôi đề xuất stack chuẩn cho v1 là:
1. `surprise_queue` (criteria có thể mượn từ SDL của Claude)
2. `equivalence_audit`
3. `proof_bundle`
4. `freeze comparison set`
5. `candidate_phenotype`
6. `prior_registry` shadow-only

**Về vai trò human**
- Tôi **không đồng ý** để human chen sâu vào early triage như một mắt xích thường trực.
- Human chỉ nên xuất hiện ở 2 điểm:
  1. ambiguity / reconstruction-risk / semantic interpretation;
  2. deployment authority sau automation.

**Ý của từng bên nên giữ**
- Giữ từ **Claude**: SDL criteria đa chiều, nhưng biến nó thành input của `surprise_queue`, không dựng thêm tiểu hệ thống cồng kềnh.
- Giữ từ **Codex**: equivalence audit + proof bundle là xương sống thật sự.
- Giữ từ **ChatGPT Pro**: discovery gates phải tách khỏi certification gates; recognition phải chấm cả **consistency motif**, không chỉ peak score.
- Giữ từ **Gemini**: semantic recovery chỉ làm lớp giải thích **sau** khi evidence đủ mạnh, không được dùng như bằng chứng.

**Trạng thái**: OPEN

**Điểm cần chốt ở vòng sau**
- Surprise criteria tối thiểu của v1 là gì?
- Equivalence metric nằm ở 008 hay 013?
- `semantic recovery` nên chạy ở Stage 7/8 hay sau Clean OOS?

---

### OI-06 — Có nên có “negative evidence / weak-signal memory” ở v1 không? Nếu có thì đến mức nào?

**Các vị trí đang có**
- **Gemini**: hầu như không xử lý explicit negative memory.
- **Codex**: dual archive + negative evidence governance.
- **Claude**: EPC để giữ weak signals tích lũy qua campaigns.
- **ChatGPT Pro**: hai loại trí nhớ + contradiction-driven search, nhưng vẫn giữ shadow-only.

**Phán quyết vòng 1**
- Tôi **ủng hộ có** memory tối thiểu ngay ở v1, nhưng chỉ ở **descriptor-level shadow-only**.
- Tôi **không ủng hộ** đưa full EPC lifecycle vào core v1.

**Mức tối thiểu nên có ở v1**
- `negative_evidence_registry.json` hoặc `contradiction_registry.json`
- chỉ lưu: descriptor/cell, failure mode, contradiction type, robustness weakness
- không lưu: answer-level threshold, winner prior, parameter direction cụ thể

**Lý do**
- Không lưu thất bại có cấu trúc thì campaign sau sẽ lặp công rất ngu.
- Nhưng nếu làm EPC full lifecycle quá sớm, ta mở thêm một mặt trận governance mới trước khi ngay cả artifact contract nền còn chưa khóa.

**Trạng thái**: OPEN

**Điểm cần chốt ở vòng sau**
- Nên dùng tên và schema nào: `negative_evidence_registry`, `contradiction_registry`, hay `epc_shadow`?
- Khi nào một weak signal đủ để đi từ “note” sang “shadow prior candidate”? 

---

### OI-07 — Cross-domain/domain-seed probing là core hay chỉ là optional input source?

**Các vị trí đang có**
- **Gemini**: xem cross-domain là lõi của discovery.
- **Claude**: CDAP có giá trị nhưng nên defer v2.
- **Codex**: không lấy cross-domain làm lõi; trọng tâm là grammar/lineage/triage.
- **ChatGPT Pro**: không xem đây là trọng tâm v1.

**Phán quyết vòng 1**
- Tôi xem cross-domain/domain-seed là **optional input source**, không phải core architecture của v1.
- Ý tưởng của Gemini **đáng giữ**, nhưng chỉ như một **curated ideation mode** ở v2 trở đi.

**Lý do**
- Nếu lấy domain seeds làm lõi quá sớm, framework rất dễ trượt sang “creative theater” thay vì discovery engine có audit.
- Trục thiếu nặng nhất hiện tại không phải “thiếu cảm hứng”, mà là thiếu **lineage, coverage, archive, proof, gate inventory**.

**Trạng thái**: OPEN

**Điểm cần chốt ở vòng sau**
- Có cần reserve một hook cho domain hints trong schema v1 không?
- Nếu có, hook đó nằm ở proposal provenance hay operator grammar?

---

### OI-08 — Descriptor taxonomy và equivalence metric nên được chốt/own thế nào?

**Các vị trí đang có**
- **Gemini**: rất ít chi tiết ở lớp taxonomy/equivalence.
- **Codex**: nhìn rõ đây là gap lớn; đề xuất `identity_equivalence_spec.md`.
- **Claude**: dùng descriptor nhiều, nhưng ownership/metric chưa khóa chặt.
- **ChatGPT Pro**: tách feature-level taxonomy (006) và strategy-level phenotype (017), nhưng metric equivalence chưa formalized đủ.

**Phán quyết vòng 1**
Tôi đề xuất split như sau:
- **Topic 006**: feature-level taxonomy, transform/operator/category ownership
- **Topic 017**: strategy phenotype descriptors, coverage map, cell definitions, prior semantics
- **Topic 008 + 013**: equivalence / distance / convergence granularity nếu thấy cần spec riêng

**Vấn đề còn mở**
- Cell dimensions tối thiểu là bao nhiêu để không vừa mù vừa nổ số cell?
- Equivalence nên đo trên descriptor bundle, daily paired returns, hay hybrid?

**Trạng thái**: OPEN

**Điểm cần chốt ở vòng sau**
- Bộ dimension tối thiểu v1
- Ranh giới giữa “same family”, “same phenotype”, “same system”, “same thing in disguise”

---

## 4) Per-agent critique cards

### 4.1 Gemini

**Luận điểm lõi**
- Discovery nên giữ offline purity.
- Cơ chế chính là cross-domain hypothesis synthesis.
- Prompt ancestry và semantic recovery giúp không làm mất “tai nạn tốt”.

**Điểm mạnh thật sự**
- Phản xạ contamination tốt.
- Nhìn đúng VDO như một dạng cross-domain import, không phải random noise.
- Có một idea tốt mà ba bản còn lại nhắc ít hơn: **semantic recovery** sau khi signal đã chứng minh.

**Điểm yếu chính**
- Quá mỏng cho bài toán này.
- Thiếu engine-level mechanics: coverage map, archive, mutation, equivalence, proof bundle, convergence, gate split.
- Dùng prompt ancestry như trục trung tâm là không đủ để đảm bảo reproducibility.
- Orthogonality + IC chỉ là một heuristic screen, chưa phải recognition pipeline đáng tin.

**Giữ lại**
- Cross-domain/domain-seed như optional ideation mode ở v2.
- Semantic recovery như lớp giải thích hậu kiểm.

**Không lấy làm backbone**
- Prompt ancestry như canonical lineage.
- Orthogonality/IC anomaly flag như recognition lane chính.

---

### 4.2 Codex

**Luận điểm lõi**
- Bài toán không chỉ là search rộng hơn, mà là phải có **discovery lineage** và biến surprise thành object có workflow riêng.

**Điểm mạnh thật sự**
- Cân bằng tốt nhất giữa discovery power và governance.
- `discovery_lineage` là một invariant rất đúng và rất đáng giữ.
- E1→E6 và R1→R6 gần như đã tạo thành một pipeline có thể draft spec được.
- Hiểu đúng firewall, shadow-only, phenotype distillation.
- Có tư duy artifact/owner tốt.

**Điểm yếu chính**
- Có nguy cơ mở thêm topic 018/019 hơi sớm nếu không kìm lại.
- Chưa nhấn đủ vào evidence stack thống kê và bài học VDO kiểu cross-timescale consistency.
- Equivalence metric và descriptor taxonomy vẫn mới ở mức khung, chưa đủ sắc để triển khai ngay.

**Giữ lại**
- Gần như toàn bộ backbone.
- Đặc biệt là: lineage, grammar, coverage, cell-elite, surprise triage, proof bundle, dual archive.

**Cần bổ sung từ bên khác**
- Lấy từ ChatGPT Pro: gate split, artifact contract, consistency motif, critical-path realism.

---

### 4.3 Claude

**Luận điểm lõi**
- X38 đang thiếu hẳn **Phase A**: ai/điều gì sẽ tạo ra VDO mới trước khi pipeline kịp scan.

**Điểm mạnh thật sự**
- Chỉ đúng chỗ đau: registry không tự mọc ra.
- GFS/APE là hai ý tưởng exploration có giá trị thật.
- SDL criteria đa chiều khá hữu ích để làm chất liệu cho surprise queue.
- Có tư duy phasing v1/v2/v3 rõ hơn các bản khác.

**Điểm yếu chính**
- Overbuild.
- SSS như explicit online subsystem là quá mạo hiểm ở thời điểm này.
- CDAP + EPC + Topic 018 cùng lúc làm tăng surface area kiến trúc quá nhanh.
- Độ rộng của GFS/APE không đi kèm một kế hoạch đủ cứng về multiplicity control, equivalence, gate inventory, invalidation.
- Có chỗ đánh giá dependency hơi lạc quan; discovery expansion vẫn chạm mạnh vào campaign model và firewall semantics.

**Giữ lại**
- Câu hỏi “Who writes VDO?” phải được giữ làm pressure test cho mọi phương án.
- GFS/APE như nguồn ý tưởng, nhưng phải đặt dưới bounded grammar và artifact contract.
- SDL criteria làm nguồn input cho surprise queue.

**Không nên lấy nguyên khối**
- Topic 018 rộng kiểu Phase A từ ngay v1.
- SSS như thành phần kiến trúc chính.
- EPC full loop như phần bắt buộc của v1.

---

### 4.4 ChatGPT Pro

**Luận điểm lõi**
- Đừng cố tái tạo một prompt may mắn; hãy xây một máy giữ đa dạng, đo consistency và khóa artifact.

**Điểm mạnh thật sự**
- Bám repo và critical path tốt nhất.
- Tách discovery gates khỏi certification gates rất đúng và rất cần.
- Descriptor tagging, coverage map, cell-elite, local probes, contradiction-driven search là bộ xương tốt cho v1.
- Nhìn ra đúng bài học VDO: **consistency motif** quan trọng hơn single-point peak.
- Chỉ rõ nhiều gap repo-level có thật: F-40→F-44, artifact gaps, evidence gaps.

**Điểm yếu chính**
- Chưa nhấn đủ discovery-lineage thành invariant như Codex.
- Còn hơi tiết chế ở mặt ideation surface area; nếu operator grammar quá hẹp thì discovery vẫn có thể bị tù.
- Weak-signal / negative-memory mới ở mức concept, chưa operational bằng Codex.

**Giữ lại**
- 017-first direction.
- discovery vs certification split.
- artifact contract + evidence stack + consistency motif.

**Cần mượn thêm từ bên khác**
- Từ Codex: lineage invariant, equivalence audit, negative evidence.
- Từ Gemini: semantic recovery như explanatory layer sau chứng minh.
- Từ Claude: pressure-test “ai viết feature mới” để không quá bảo thủ.

---

## 5) Interim Merge Direction (đề xuất hợp nhất tạm sau vòng 1)

### 5.1 Backbone nên lấy

**Backbone v1 nên là `Codex + ChatGPT Pro`, với ba chỉnh sửa quan trọng:**

1. **Nâng discovery lineage lên thành invariant bắt buộc**
   - lấy từ Codex.

2. **Khóa chặt gate split + artifact contract từ đầu**
   - lấy từ ChatGPT Pro.

3. **Không cho SSS/CDAP/EPC full loop trở thành core v1**
   - phản biện Claude/Gemini theo hướng defer có kiểm soát.

### 5.2 Những gì nên ADOPT NGAY cho draft/spec

1. `discovery_lineage.json`
2. `operator_registry.json`
3. `candidate_genealogy.json`
4. `coverage_map.*`
5. `cell_elite_archive.*`
6. `keep_drop_ledger.*`
7. bounded `operator_grammar`
8. `probe_candidates` / local-neighborhood probes
9. `surprise_queue`
10. `equivalence_audit`
11. `proof_bundle`
12. `comparison_set/`
13. `phenotype_pack/`
14. `epistemic_delta.json`
15. `prior_registry.json` shadow-only
16. `discovery_gate_inventory.md`
17. `discovery_artifact_contract.md`

### 5.3 Những gì nên DEFER

1. `CDAP` như một subsystem riêng
2. domain-seed prompting như engine trung tâm
3. `SSS` theo nghĩa online phase rõ ràng
4. `EPC` full lifecycle và maturity ladder
5. GFS depth 2/3 ở quy mô lớn
6. topic umbrella mới nếu chưa thật cần

### 5.4 Ownership tạm khuyến nghị

| Owner | Nên gánh gì |
|---|---|
| **006** | feature/operator grammar, transform registry, feature taxonomy, compiled manifest ingestion |
| **017** | coverage map, cell-elite archive, local probes, surprise semantics, contradiction profile, phenotype/prior semantics, budget governor, epistemic_delta |
| **015** | artifact enumeration, schema contract, invalidation semantics |
| **013** | convergence in descriptor-space, stop logic, phần gate-inventory nếu cần |
| **008** | identity/equivalence semantics nếu cần formal relation model |
| **003** | wiring vào pipeline sau khi upstream đã khóa |

---

## 6) Những đề xuất/spec nên mở tiếp theo sau vòng 1

> Đây không phải kết luận cuối cùng, mà là hướng làm việc thực dụng nhất sau vòng này.

### Ưu tiên cao
1. `discovery_artifact_contract.md`
2. `discovery_gate_inventory.md`
3. `operator_grammar_and_local_probes.md`
4. `identity_equivalence_spec.md` (nếu 008/013 thấy cần tách)

### Ưu tiên vừa
1. `negative_evidence_registry` schema
2. `semantic_recovery` note format
3. `bounded_ideation_lane` contract

### Chưa nên ưu tiên v1
1. `Topic 018` theo nghĩa umbrella rộng
2. `CDAP` / domain catalog
3. `EPC` full lifecycle

---

## 7) Agenda cho vòng sau

Chỉ bàn các ID sau:
- `OI-01` Topic mới hay fold vào topic cũ
- `OI-02` bounded ideation lane vs SSS
- `OI-03` minimum viable v1 scope
- `OI-04` canonical lineage schema
- `OI-05` recognition stack + human role
- `OI-06` negative evidence / weak-signal memory scope
- `OI-07` cross-domain priority
- `OI-08` descriptor taxonomy + equivalence ownership

### Cách phản hồi đề nghị cho agent vòng sau

Dùng format ngắn gọn theo từng issue:

```md
## OI-0X
- Stance: AGREE / DISAGREE / AMEND
- Điểm đồng ý:
- Điểm phản đối:
- Đề xuất sửa:
- Bằng chứng repo (nếu có):
```

Không cần viết lại toàn bộ debate landscape.

---

## 8) Change Log

### Round 1 — 2026-03-25 — chatgptpro
- Đã review `request.md` và 4 proposal vòng đầu.
- Chọn `codex_propone.md` làm baseline chính.
- Chọn `chatgptpro_propone.md` làm co-baseline về guardrail và bám repo.
- Đưa 8 điểm sang `Convergence Ledger`.
- Mở 8 `Open Issues` cho các vòng sau.
- Chốt format file làm mẫu để tránh loạn thông tin ở nhiều vòng tranh luận.

