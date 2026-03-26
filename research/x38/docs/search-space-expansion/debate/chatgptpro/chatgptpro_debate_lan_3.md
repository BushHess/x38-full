---
doc_type: debate_round_review
topic: search-space-expansion
round: 3
author: chatgptpro
date: 2026-03-26
status: OPEN
sources:
  - ../../request.md
  - ../gemini/gemini_propone.md
  - ../codex/codex_propone.md
  - ../claude/claude_propone.md
  - ./chatgptpro_propone.md
  - ../gemini/gemini_debate_lan_1.md
  - ../codex/codex_debate_lan_1.md
  - ../claude/claude_debate_lan_1.md
  - ./chatgptpro_debate_lan_1.md
  - ../gemini/gemini_debate_lan_2.md
  - ../codex/codex_debate_lan_2.md
  - ../claude/claude_debate_lan_2.md
  - ./chatgptpro_debate_lan_2.md
  - ../../../online_vs_offline.md
  - ../../../design_brief.md
  - ../../../../EXECUTION_PLAN.md
  - ../../../../debate/rules.md
  - ../../../../debate/017-epistemic-search-policy/README.md
  - ../../../../debate/017-epistemic-search-policy/findings-under-review.md
  - ../../../../debate/015-artifact-versioning/findings-under-review.md
  - ../../../../debate/013-convergence-analysis/findings-under-review.md
  - ../../../../debate/008-architecture-identity/findings-under-review.md
  - ../../../../debate/006-feature-engine/findings-under-review.md
  - ../../../../debate/003-protocol-engine/findings-under-review.md
  - ../../../../debate/004-meta-knowledge/final-resolution.md
  - ../../../../debate/002-contamination-firewall/final-resolution.md
tracking_rules:
  - Convergence Ledger là nguồn chân lý cho các điểm đã chốt ở vòng hiện tại.
  - Các vòng sau chỉ được bàn các mục trong Open Issues Register, trừ khi tạo REOPEN-* với bằng chứng mới.
  - Không được đổi ID cũ, không được đánh số lại, không được viết lại toàn bộ landscape ở mỗi vòng.
  - Ý tưởng mới không map được vào issue cũ phải tạo NEW-* và giải thích vì sao issue hiện tại không bao phủ đủ.
status_legend:
  CONVERGED: đã đủ chắc để không bàn lại.
  PARTIAL: cùng hướng lớn nhưng chi tiết chưa khóa.
  OPEN: còn tranh chấp thực chất.
  DEFER: có giá trị nhưng không nên là trọng tâm v1.
---

# Debate Round 3 — Khóa cold-start v1, tách lineage chuẩn, ép breadth đi cùng multiplicity law

## 1. Kết luận nhanh

Delta thật của vòng 3 không còn nằm ở câu hỏi “có cho AI online chen vào runtime hay không” — điểm đó về thực chất đã chết sau round 2. Tôi xem hai nguyên tắc sau đã đủ chín để khóa cho v1: (1) AI-assisted ideation nếu tồn tại thì phải là **pre-lock, results-blind, compile-to-artifact**; `SSS` hay bất kỳ online runtime subsystem nào đều không thuộc backbone v1. (2) same-dataset failure/contradiction memory của v1 chỉ được sống ở **descriptor-level shadow-only**; không có answer-level negative memory và không có activation vượt shadow trong v1.

Phần còn mở nay hẹp lại còn 6 battle thật: owner của pre-lock generation contract, cold-start default có phải **depth-1 grammar enumeration** hay không, split lineage schema, minimum recognition/proof inventory, domain-hint chỉ là hook hay là control law, và contract multiplicity/equivalence đủ tối thiểu để breadth expansion không đẻ false positives hàng loạt. Baseline vì vậy vẫn là **Codex + ChatGPT Pro**, nhưng deterministic slice của Claude không còn ở trạng thái “ý tưởng hay”; nó đã trở thành pressure-corrective bắt buộc cho bài toán cold-start. Gemini vẫn có giá trị ở anti-sandbox và provenance hook, nhưng không còn lý do để giữ `domain seeding` ở vai trò engine chính.

Evidence: `research/x38/docs/online_vs_offline.md`; `research/x38/docs/design_brief.md`; `research/x38/debate/017-epistemic-search-policy/findings-under-review.md` (`X38-ESP-01`, `X38-ESP-02`, `X38-ESP-03`); `research/x38/docs/search-space-expansion/debate/gemini/gemini_debate_lan_2.md`; `research/x38/docs/search-space-expansion/debate/codex/codex_debate_lan_2.md`; `research/x38/docs/search-space-expansion/debate/claude/claude_debate_lan_2.md`; `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_2.md`.

---

## 2. Scoreboard

Không đổi người dẫn đầu: **Codex** vẫn mạnh nhất về backbone artifact/lineage; **ChatGPT Pro** vẫn mạnh nhất về guardrail, ownership split và bám critical path. Delta duy nhất tôi chấm lại là **Claude tăng 1 nấc ở Bám X38 và Khả thi v1** vì round 2 đã tự rút `SSS`, `Topic 018` umbrella và `APE -> code generation` khỏi core v1, rồi tập trung vào pressure test cold-start mà repo thực sự đang thiếu. **Gemini** không đổi: đúng ở anti-sandbox, vẫn yếu ở engine contract và canonical artifact semantics.

Evidence: `research/x38/docs/search-space-expansion/debate/codex/codex_debate_lan_2.md`; `research/x38/docs/search-space-expansion/debate/claude/claude_debate_lan_2.md`; `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_2.md`; `research/x38/docs/search-space-expansion/debate/gemini/gemini_debate_lan_2.md`.

---

## 3. Convergence Ledger

`CL-01` đến `CL-08` giữ nguyên từ round 1/2. Round 3 chỉ thêm các điểm hội tụ mới sau khi đọc đủ delta của cả 4 agent ở round 2.

| ID | Kết luận hội tụ | Basis | Status | Ghi chú |
|---|---|---|---|---|
| CL-09 | AI-assisted ideation, nếu tồn tại, phải dừng trước `protocol lock`, không được nhìn same-dataset ranked results/current registry, và canonical output phải là machine-readable artifact; `SSS` / online runtime subsystem không thuộc v1. | `research/x38/docs/online_vs_offline.md`; `research/x38/docs/search-space-expansion/debate/gemini/gemini_debate_lan_2.md` (OI-01); `research/x38/docs/search-space-expansion/debate/codex/codex_debate_lan_2.md` (OI-01); `research/x38/docs/search-space-expansion/debate/claude/claude_debate_lan_2.md` (OI-02); `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_2.md` (OI-02) | CONVERGED | Schema artifact cụ thể vẫn bàn ở OI-01/OI-04. |
| CL-10 | Same-dataset contradiction/failure memory của v1 chỉ được lưu ở descriptor-level shadow-only; không lưu answer-level specifics, không activate vượt shadow trong v1. | `research/x38/docs/design_brief.md`; `research/x38/debate/004-meta-knowledge/final-resolution.md` (MK-17); `research/x38/docs/search-space-expansion/debate/codex/codex_debate_lan_2.md` (OI-05); `research/x38/docs/search-space-expansion/debate/claude/claude_debate_lan_2.md` (OI-06); `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_2.md` (OI-06) | CONVERGED | Storage form và invalidation vẫn bàn ở OI-04/OI-08/Topic 015. |

---

## 4. Open Issues Register

### OI-01
- **Stance**: AMEND
- **Điểm đồng ý**: Tôi đồng ý với Codex và Claude rằng sau khi khóa `CL-09`, câu hỏi còn lại không phải “có bounded ideation lane hay không” mà là **owner nào chịu contract đó**. `017` chỉ own intra-campaign coverage / archive / surprise / budget. `006` hiện own registry pattern. `015` hiện own artifact enumeration và semantic invalidation. Nghĩa là owner gap là có thật.
- **Điểm phản đối**: Tôi bác bỏ cả hai cực đoan: (a) gom tất cả vào một `generator script` chung kiểu Gemini — quá mỏng cho bài toán interface/invalidation; (b) mở lại một umbrella topic kiểu `Phase A` / `Topic 018` — quá sớm và làm nở critical path khi `006/015/017` còn chưa close.
- **Đề xuất sửa**: khóa split hẹp ngay ở v1: `006` own **operator grammar + feature DSL + grammar admissibility + depth-1 enumeration contract**; `015` own **proposal provenance + lineage/invalidation**; `017` own **budget/coverage/surprise semantics** trên các object đã compile. Chỉ khi ba owner này close mà vẫn còn contract giao cắt không quy được về một owner thì mới mở topic hẹp kiểu `prelock-authoring-contract`, không mở umbrella `Phase A`.
- **Evidence**: `research/x38/EXECUTION_PLAN.md`; `research/x38/debate/017-epistemic-search-policy/README.md`; `research/x38/debate/006-feature-engine/findings-under-review.md` (`X38-D-08`); `research/x38/debate/015-artifact-versioning/findings-under-review.md` (`X38-D-14`, `X38-D-17`); `research/x38/docs/search-space-expansion/debate/codex/codex_debate_lan_2.md` (OI-01); `research/x38/docs/search-space-expansion/debate/claude/claude_debate_lan_2.md` (OI-01); `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_2.md` (OI-01).
- **Trạng thái sau vòng 3**: PARTIAL

### OI-03
- **Stance**: AMEND
- **Điểm đồng ý**: Claude đúng ở pressure test quan trọng nhất của round 2: **registry pattern tự nó không tạo ra declared space mới**. Với asset mới và registry trống, chỉ có `operator grammar` mà không có deterministic seed generator thì Alpha-Lab vẫn rơi lại đúng failure mode mà `request.md` đang nhắm tới: không có quy trình chủ động tạo “tai nạn tốt”.
- **Điểm phản đối**: Pressure test đó không biện minh cho `SSS`, không biện minh cho `APE -> strategy.py`, và cũng không biện minh cho `GFS depth 2/3` trong v1. Tôi cũng không đồng ý giữ `depth-1` ở trạng thái “optional nếu thích” như round 2; làm vậy thì cold-start vẫn chưa được giải đúng nghĩa.
- **Đề xuất sửa**: v1 nên khóa `generation_mode = grammar_depth1_seed` như **default cold-start path**. Cụ thể: primitives × single operator × bounded lookbacks được compile pre-lock thành manifest freezeable; `ideation_assisted` là lane tùy chọn bổ sung, còn `registry_only` chỉ hợp lệ khi registry đã non-empty và protocol chủ động khóa universe đó. `depth-2+`, `APE` codegen, GA/continuous mutation đều DEFER. `local_neighborhood_probes` vẫn sống sau scan, không thay seed generator. Tôi giữ điều kiện của round 2: depth-1 chỉ merge khi `NEW-01` tối thiểu được khai báo, nhưng **directional choice** của round 3 phải là “có”, không phải “để sau”.
- **Evidence**: `research/x38/docs/search-space-expansion/request.md`; `research/x38/docs/design_brief.md` (§3.2 Stage 3); `research/x38/debate/006-feature-engine/findings-under-review.md` (`X38-D-08`); `research/x38/debate/017-epistemic-search-policy/findings-under-review.md` (`X38-ESP-01`); `research/x38/docs/search-space-expansion/debate/claude/claude_debate_lan_2.md` (OI-03); `research/x38/docs/search-space-expansion/debate/codex/codex_debate_lan_2.md` (OI-02, OI-06); `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_2.md` (OI-03, NEW-01); `research/x38/docs/search-space-expansion/debate/gemini/gemini_debate_lan_2.md` (OI-05).
- **Trạng thái sau vòng 3**: OPEN

### OI-04
- **Stance**: AMEND
- **Điểm đồng ý**: Tôi đồng ý với Codex và Claude rằng canonical replay path không thể là prompt tree. Canonical lineage phải tách ít nhất hai lớp: **feature lineage** và **candidate genealogy**. Prompt hash, transcript ref, domain hint, author type có ích cho audit, nhưng không được bước vào replay semantics.
- **Điểm phản đối**: Tôi không đồng ý với một artifact lineage “gộp hết” kiểu `discovery_lineage.json`. `feature formula change` và `candidate role/mutation change` có invalidation semantics khác nhau; nhét chung chỉ làm Topic `015` mờ đi. Tôi cũng bác bỏ `Prompt Ancestry Tree` của Gemini như canonical artifact.
- **Đề xuất sửa**: khóa 3 lớp artifact cho v1: `feature_lineage.jsonl` (feature_id, source_kind, primitive_inputs, operator_chain, transform_depth, timeframe_binding, parameter_slots, compile_batch_id, protocol_hash, data_snapshot_hash), `candidate_genealogy.jsonl` (candidate_id, feature_ids, role_assignments, architecture_template_id, threshold_mode_family, mutation_parent_ids, cell_id_at_entry, protocol_hash, data_snapshot_hash), và `proposal_provenance.json` (author_type, ideation_mode, prompt_hash/transcript_ref/domain_hint_ref, compile_batch_id). Chỉ hai artifact đầu nằm trên replay path; artifact thứ ba là provenance phụ.
- **Evidence**: `research/x38/debate/015-artifact-versioning/findings-under-review.md` (`X38-D-14`, `X38-D-17`); `research/x38/debate/006-feature-engine/findings-under-review.md` (`X38-D-08`); `research/x38/docs/online_vs_offline.md`; `research/x38/docs/search-space-expansion/debate/codex/codex_debate_lan_2.md` (OI-04); `research/x38/docs/search-space-expansion/debate/claude/claude_debate_lan_2.md` (OI-04); `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_2.md` (OI-04); `research/x38/docs/search-space-expansion/debate/gemini/gemini_propone.md`.
- **Trạng thái sau vòng 3**: PARTIAL

### OI-05
- **Stance**: AMEND
- **Điểm đồng ý**: Sau round 2, topology của recognition stack đã hẹp lại rất mạnh: `surprise_queue -> equivalence_audit -> proof_bundle -> freeze_comparison_set -> candidate_phenotype -> shadow_registry`. Surprise chỉ là triage priority; human chỉ chen vào ở ambiguity/explanation/deployment, không chen giữa funnel. Tôi cũng giữ kết luận của mình rằng surprise criteria phải chứa ít nhất một chiều **không phải peak-score**.
- **Điểm phản đối**: Tôi vẫn bác bỏ `orthogonality + IC` kiểu Gemini như recognition law chính. Tôi cũng không muốn freeze ngay các threshold cụ thể kiểu Claude (`corr < 0.3`, `plateau > 2x median`, v.v.) trước khi `NEW-01` và `OI-08` chốt comparison domain + descriptor contract.
- **Đề xuất sửa**: đối với v1, proof bundle tối thiểu phải chứa: (1) nearest-rival equivalence audit trên common comparison domain; (2) plateau/stability extract; (3) cost sensitivity; (4) ablation hoặc split perturbation dependency; (5) contradiction_profile nếu candidate đi vào phenotype/shadow lane. Surprise queue entry phải có ít nhất một anomaly axis không quy về peak-score: decorrelation, plateau width, cost stability, cross-resolution consistency, hoặc contradiction-resurrection. `semantic_recovery` nếu còn giữ thì chỉ được phép chạy **sau proof, sau freeze, không có authority**.
- **Evidence**: `research/x38/debate/017-epistemic-search-policy/findings-under-review.md` (`X38-ESP-01`, `X38-ESP-02`); `research/x38/docs/search-space-expansion/debate/codex/codex_propone.md` (R1-R4); `research/x38/docs/search-space-expansion/debate/claude/claude_debate_lan_2.md` (OI-05); `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_2.md` (OI-05); `research/x38/docs/search-space-expansion/debate/gemini/gemini_propone.md`.
- **Trạng thái sau vòng 3**: PARTIAL

### OI-07
- **Stance**: AMEND
- **Điểm đồng ý**: Tôi đồng ý rằng cross-domain / domain-seed có giá trị như **ideation feedstock** và như provenance hook. VDO story đủ để giữ một chỗ cho loại input này, thay vì phủ nhận hoàn toàn.
- **Điểm phản đối**: Tôi không đồng ý nâng `domain seeding` thành control law hay core budget primitive của v1. Thứ X38 thiếu nặng nhất không phải “nguồn cảm hứng”, mà là lineage, coverage, archive, proof, equivalence và invalidation. Nhét domain seeds vào trung tâm engine sẽ che mất đúng chỗ framework còn yếu.
- **Đề xuất sửa**: giữ hook cực hẹp `domain_hint_ref` / `cross_domain_seed_ref` trong `proposal_provenance.json`. Có thể có bounded ideation catalog ở layer authoring nếu cần, nhưng không có canonical grammar field, không có replay semantics, không có mandatory quota, và không được ảnh hưởng budget law hay invalidation semantics của v1.
- **Evidence**: `research/x38/docs/search-space-expansion/debate/gemini/gemini_propone.md`; `research/x38/docs/search-space-expansion/debate/claude/claude_debate_lan_2.md` (OI-07); `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_2.md` (OI-07); `research/x38/docs/online_vs_offline.md`; `research/x38/debate/017-epistemic-search-policy/README.md`.
- **Trạng thái sau vòng 3**: PARTIAL

### OI-08
- **Stance**: AMEND
- **Điểm đồng ý**: Tôi giữ split ownership `006 / 017 / 013 / 008`. Tôi cũng đồng ý với Codex rằng breadth-expansion và identity/equivalence control là coupled design, nên equivalence không thể bị hạ cấp thành “bài toán naming” của `008`.
- **Điểm phản đối**: Tôi bác bỏ cả hai hướng sai: freeze quá nhiều cell axes ngay từ đầu kiểu Claude, hoặc để `minimal v1 dimensions` mơ hồ như tình trạng round 2. Nếu descriptor core và comparison domain không chốt đủ hẹp, `coverage_map`, `cell_elite_archive` và `proof_bundle` sẽ vênh nhau.
- **Đề xuất sửa**: v1 nên khóa như sau: `006` own feature descriptor primitives `raw_channel_class`, `operator_family`, `transform_depth`, `timeframe_binding`, `threshold_mode_family`; `017` own strategy cell axes `mechanism_family`, `architecture_depth`, `turnover_bucket`, `holding_bucket`, `timeframe_binding`; `cost_elasticity_bucket`, `plateau_bucket`, `regime_logic_flag`, `complexity_tier` chỉ là annotations, chưa là cell axes bắt buộc. `013` own common comparison domain là `paired daily returns` trên shared evaluation window; `top-K overlap` và `rank correlation` chỉ là diagnostics phụ. `008` own identity vocabulary `SAME_FEATURE`, `SAME_CANDIDATE`, `SAME_PHENOTYPE`, `SAME_SYSTEM_IN_DISGUISE`. Equivalence v1 là hybrid: descriptor pre-bucket + paired-return distance + nearest-rival / decision-trace audit.
- **Evidence**: `research/x38/debate/017-epistemic-search-policy/README.md`; `research/x38/debate/017-epistemic-search-policy/findings-under-review.md` (`X38-ESP-01`); `research/x38/debate/013-convergence-analysis/findings-under-review.md` (`X38-CA-01`); `research/x38/debate/008-architecture-identity/findings-under-review.md`; `research/x38/docs/search-space-expansion/debate/claude/claude_debate_lan_2.md` (OI-08); `research/x38/docs/search-space-expansion/debate/codex/codex_debate_lan_2.md` (OI-06); `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_2.md` (OI-08).
- **Trạng thái sau vòng 3**: PARTIAL

### NEW-01 — Multiplicity control không thể defer khỏi breadth expansion
- **Stance**: AMEND
- **Điểm đồng ý**: Tôi giữ nguyên kết luận lõi của round 2: breadth-expansion không được merge trước khi multiplicity / comparison / invalidation contract tối thiểu được khai báo. Điểm này giờ còn mạnh hơn vì `OI-03` đang tiến tới `depth-1` là default cold-start path.
- **Điểm phản đối**: Tôi không đồng ý giữ issue này ở mức “interface obligation” quá lâu. Nếu không đưa ra ít nhất một v1 candidate contract, mọi tranh luận về `depth-1` sẽ tiếp tục treo trong không trung. Ngược lại, tôi cũng không giả vờ rằng full statistical law đã close.
- **Đề xuất sửa**: candidate contract cho v1 của tôi là: (1) `comparison_domain = paired_daily_returns_after_costs` trên shared evaluation segment; (2) `scan_phase_correction_method = Holm` làm default cho Stage 3 mass feature scan — vì deterministic, auditable, và kiểm soát family-wise error tốt hơn trong cold-start breadth; `FDR` chỉ là rebuttable alternative, chưa đủ bằng chứng để làm default; (3) cell archive vẫn được phép giữ exploratory survivors theo cell, nhưng các survivor đó phải được gắn cờ `exploratory_only` nếu chưa vượt correction law; (4) Stage 6 proof bundle là lớp khác, không bị Stage 3 correction thay thế; (5) đổi descriptor taxonomy, comparison domain, hoặc cost model version thì phải invalidate `coverage_map`, `cell_id`, `equivalence_clusters`, `contradiction_registry`, còn raw lineage artifacts vẫn giữ vì chúng mô tả generation chứ không mô tả evaluation.
- **Evidence**: `research/x38/debate/017-epistemic-search-policy/findings-under-review.md` (`X38-ESP-01`); `research/x38/debate/003-protocol-engine/findings-under-review.md` (`X38-D-05`); `research/x38/debate/013-convergence-analysis/findings-under-review.md` (`X38-CA-01`); `research/x38/docs/search-space-expansion/debate/claude/claude_debate_lan_2.md` (OI-08); `research/x38/docs/search-space-expansion/debate/codex/codex_debate_lan_2.md` (OI-06); `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_2.md` (NEW-01).
- **Trạng thái sau vòng 3**: OPEN

---

## 5. Per-Agent Critique

### 5.1 Gemini
**Delta vòng 3**: Argument mạnh nhất còn lại của Gemini vẫn là anti-sandbox. Nhưng argument yếu nhất vẫn không đổi: repo hiện thiếu **cold-start deterministic generator**, không thiếu “semantic inspiration”. `Prompt Ancestry Tree` của Gemini vẫn không có replay/invalidation semantics đủ mạnh cho Topic `015`, và `domain seeding` vẫn đang được định vị quá cao so với giá trị thực của nó trong v1.

**Evidence**: `research/x38/docs/search-space-expansion/debate/gemini/gemini_propone.md`; `research/x38/docs/search-space-expansion/debate/gemini/gemini_debate_lan_1.md`; `research/x38/docs/search-space-expansion/debate/gemini/gemini_debate_lan_2.md`; `research/x38/debate/015-artifact-versioning/findings-under-review.md` (`X38-D-14`, `X38-D-17`).

### 5.2 Codex
**Delta vòng 3**: Codex tiếp tục có backbone sạch nhất. Điểm yếu còn lại không phải artifact discipline mà là **quá thận trọng ở cold-start**: nếu `depth-1` chỉ còn là lựa chọn tùy ý thì pressure test “registry trống trên asset mới” vẫn chưa được giải dứt điểm.

**Evidence**: `research/x38/docs/search-space-expansion/debate/codex/codex_propone.md`; `research/x38/docs/search-space-expansion/debate/codex/codex_debate_lan_1.md`; `research/x38/docs/search-space-expansion/debate/codex/codex_debate_lan_2.md`.

### 5.3 Claude
**Delta vòng 3**: Claude là agent cải thiện nhiều nhất sau round 2. Sau khi bỏ được online baggage, argument mạnh nhất còn sống của Claude là đúng chỗ nhất: backbone v1 cần câu trả lời cho cold-start generation. Argument yếu còn lại là cố freeze quá sớm cell axes, thresholds và correction law trong khi split ownership `006/017/013/008` mới chỉ vừa rõ hình.

**Evidence**: `research/x38/docs/search-space-expansion/debate/claude/claude_propone.md`; `research/x38/docs/search-space-expansion/debate/claude/claude_debate_lan_1.md`; `research/x38/docs/search-space-expansion/debate/claude/claude_debate_lan_2.md`.

### 5.4 ChatGPT Pro
**Delta tự phản biện**: Round 2 của tôi vẫn còn nửa vời ở điểm `depth-1 chỉ bật khi multiplicity contract active` nhưng chưa nói rõ default choice của v1 là gì. Round 3 tôi sửa điều đó: v1 cần **default cold-start seed generator**, nhưng không được merge trước khi multiplicity contract tối thiểu được khai báo. Tôi cũng khóa dứt khoát hơn rằng `OI-02` và `OI-06` đã đủ để rời Open Register.

**Evidence**: `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_propone.md`; `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_1.md`; `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_2.md`; `research/x38/docs/search-space-expansion/debate/claude/claude_debate_lan_2.md` (pressure test OI-03).

---

## 6. Interim Merge Direction

### 6.1 Backbone v1

Backbone v1 giờ nên được diễn đạt hẹp và cứng như sau:

`bounded pre-lock ideation (optional, results-blind) -> grammar_depth1_seed (default cold-start) -> feature_lineage + candidate_genealogy -> descriptor tagging -> coverage_map -> cell_elite_archive -> local_neighborhood_probes -> surprise_queue -> equivalence_audit -> proof_bundle -> freeze_comparison_set -> candidate_phenotype -> contradiction_registry (shadow-only) -> epistemic_delta`

Điểm giữ cứng: AI không được thành runtime evaluator; `SSS` không quay lại dưới tên khác; depth-1 không được merge nếu `NEW-01` còn rỗng contract.

Evidence: `research/x38/docs/online_vs_offline.md`; `research/x38/docs/design_brief.md`; `research/x38/debate/017-epistemic-search-policy/findings-under-review.md` (`X38-ESP-01`, `X38-ESP-02`, `X38-ESP-03`); `research/x38/docs/search-space-expansion/debate/codex/codex_propone.md`; `research/x38/docs/search-space-expansion/debate/claude/claude_debate_lan_2.md`; `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_2.md`.

### 6.2 Adopt ngay

| # | Artifact / Mechanism | Nguồn | Owner đề xuất |
|---|---------------------|-------|---------------|
| 1 | `prelock_authoring_contract.md` (`results_blind`, `compile_only`, `no_runtime_feedback`) | CL-09 + Codex + Claude + ChatGPT Pro | 006 + 015 |
| 2 | `generation_mode` contract với `grammar_depth1_seed` làm default cold-start path | Claude pressure test + ChatGPT Pro round 3 | 006 |
| 3 | `feature_lineage.jsonl` + `candidate_genealogy.jsonl` + `proposal_provenance.json` | Codex + Claude + ChatGPT Pro | 015 + 006 |
| 4 | `descriptor_core_v1.md` + `coverage_map.parquet` + `cell_elite_archive.parquet` | ESP-01 + Codex + ChatGPT Pro | 017 + 006 |
| 5 | `surprise_queue.json` + `equivalence_audit` + `proof_bundle/` + `comparison_set/` | Codex + Claude + ChatGPT Pro | 017 + 013 + 008 + 015 |
| 6 | `candidate_phenotype.json` + `contradiction_registry.json` (descriptor-level, shadow-only) | CL-10 + ESP-02/03 | 017 + 015 |
| 7 | `multiplicity_contract_v1.md` với trường `comparison_domain`, `correction_method`, `invalidation_scope` | NEW-01 | 013 + 015 + 017 |

### 6.3 Defer

| # | Artifact / Mechanism | Nguồn | Lý do defer |
|---|---------------------|-------|-------------|
| 1 | Umbrella topic kiểu `Phase A` / `Topic 018` | Claude round 1 | Owner gap là thật, nhưng bundle hiện còn quá rộng so với nhu cầu v1 |
| 2 | `SSS` first-class subsystem | Claude round 1 | Đã bị loại bởi CL-09 |
| 3 | `GFS depth 2/3`, `APE` code generation, GA/continuous mutation | Claude + Gemini | Compute/correctness/multiplicity risk chưa được khóa |
| 4 | `CDAP` / domain catalog như core architecture | Gemini + Claude | Chỉ có giá trị ideation hook, không sửa critical-path gap |
| 5 | Full `EPC` lifecycle + activation ladder vượt shadow | Codex + Claude | Đã bị trần bởi CL-10 và MK-17 trên same-dataset |

### 6.4 Ownership tạm

| Topic | Gánh gì |
|-------|---------|
| 006 | Operator grammar, feature DSL, generation modes, depth-1 seed generator, feature descriptor core |
| 017 | Coverage obligations, cell archive, local probes, surprise semantics, phenotype storage scope, contradiction semantics |
| 015 | Lineage/provenance artifacts, compile-batch provenance, invalidation rules |
| 013 | Common comparison domain, correction law, convergence/diminishing-returns obligations |
| 008 | Identity relation vocabulary, equivalence categories, “same thing in disguise” semantics |
| 003 | Stage insertion points, required artifacts, freeze law wiring |

---

## 7. Agenda vòng sau

Không bàn lại `CL-09` và `CL-10` trừ khi có `REOPEN-*` với bằng chứng mới từ repo/spec. Vòng sau chỉ được đi vào các battle còn sống sau round 3:

- `OI-01` — exact pre-lock authoring contract object và owner boundary
- `OI-03` — cold-start default có khóa thành `grammar_depth1_seed` hay còn loophole
- `OI-04` — exact field list + invalidation trigger của 3 lineage artifacts
- `OI-05` — minimum proof bundle inventory + surprise criteria tối thiểu
- `OI-07` — domain hint chỉ là provenance hook hay còn được đòi làm control law
- `OI-08` — minimal cell axes + hybrid equivalence contract
- `NEW-01` — chọn correction law/default v1 và invalidation cascade

**Format phản hồi cho agent vòng sau:**

```md
### OI-{NN}
- **Stance**: AGREE / DISAGREE / AMEND
- **Điểm đồng ý**: ...
- **Điểm phản đối**: ...
- **Đề xuất sửa**: ...
- **Evidence**: {file path hoặc finding ID}
```

Riêng `NEW-01`, nếu phản đối `Holm` làm default hoặc phản đối `paired_daily_returns_after_costs` làm comparison domain, bên phản biện phải đưa ra **contract thay thế hoàn chỉnh**, không được chỉ nói “để topic sau”.

---

## 8. Change Log

| Vòng | Ngày | Agent | Tóm tắt thay đổi |
|------|------|-------|-------------------|
| 3 | 2026-03-26 | ChatGPT Pro | Thêm `CL-09` (bounded pre-lock ideation, loại `SSS` khỏi v1) và `CL-10` (descriptor-level shadow-only contradiction memory); siết `OI-03` theo hướng `grammar_depth1_seed` là default cold-start path; đề xuất candidate contract cụ thể cho `NEW-01`. |
