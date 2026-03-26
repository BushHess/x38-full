---
doc_type: debate_round_review
topic: search-space-expansion
round: 2
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
  - ../../../../debate/001-campaign-model/findings-under-review.md
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

# Debate Round 2 — Khóa hẹp backbone v1, chưa hợp thức hóa online-first Phase A

## 1. Kết luận nhanh

Baseline của tôi không đổi: backbone v1 vẫn là **Codex + ChatGPT Pro**, còn Claude vẫn là pressure-test hữu ích nhất cho câu hỏi “ai viết feature mới?”, nhưng chưa chứng minh được rằng `Topic 018 + SSS + GFS/APE bundle` là gói tối thiểu đúng cho v1. Gemini vẫn có hai hạt nhân nên giữ — anti-sandbox và semantic recovery hậu kiểm — nhưng vẫn chưa cung cấp engine-level mechanics đủ cứng để làm backbone.

Delta quan trọng nhất sau khi đọc đủ 4 file round 1 là: câu hỏi owner cho **pre-lock generation lane** là có thật, nhưng câu trả lời v1 không phải “thêm một online subsystem”, mà là **bounded pre-lock authoring contract** biên dịch về manifest/grammar freezeable trước Stage 1. Delta thứ hai: breadth expansion không được đi một mình; nếu không khóa đồng thời multiplicity/equivalence control, surprise lane sẽ trượt thành false-positive lane. Delta thứ ba: canonical lineage nên tách rõ **feature lineage** khỏi **candidate genealogy**; prompt/session ancestry chỉ nên là provenance phụ, không nằm trên replay path.

Evidence: `research/x38/docs/search-space-expansion/debate/codex/codex_debate_lan_1.md`; `research/x38/docs/search-space-expansion/debate/claude/claude_debate_lan_1.md`; `research/x38/docs/search-space-expansion/debate/gemini/gemini_debate_lan_1.md`; `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_1.md`; `research/x38/docs/online_vs_offline.md`; `research/x38/debate/017-epistemic-search-policy/findings-under-review.md` (`X38-ESP-01`, `X38-ESP-02`, `X38-ESP-03`).

---

## 2. Scoreboard

Không đổi điểm số tổng thể so với round 1. Thứ tự vẫn là: **Codex** mạnh nhất về backbone discovery; **ChatGPT Pro** mạnh nhất về guardrail và critical-path fit; **Claude** mạnh nhất về pressure-test missing-Phase-A nhưng vẫn overbuild; **Gemini** giữ vài ý đúng nhưng chưa đủ artifact/mechanism để làm xương sống.

Evidence: `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_1.md`; `research/x38/docs/search-space-expansion/debate/codex/codex_debate_lan_1.md`; `research/x38/docs/search-space-expansion/debate/claude/claude_debate_lan_1.md`; `research/x38/docs/search-space-expansion/debate/gemini/gemini_debate_lan_1.md`.

---

## 3. Convergence Ledger

Không thêm `CL-*` mới và không tạo `REOPEN-*` trong vòng này. Các điểm gần chốt như canonical lineage, shadow-only memory ceiling, và vai trò optional của domain hints mới đạt mức **cùng hướng lớn**, chưa đạt ngưỡng `CONVERGED` theo `debate/rules.md` §7-§9 vì chưa có steel-man confirmation rõ giữa các agent.

Evidence: `research/x38/debate/rules.md` (§7-§9); `research/x38/docs/search-space-expansion/debate/codex/codex_debate_lan_1.md`; `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_1.md`.

---

## 4. Open Issues Register

### OI-01
- **Stance**: AMEND
- **Điểm đồng ý**: Tôi đồng ý với Claude và Codex rằng có một owner gap thật cho **pre-lock generation lane**; `017` hiện own intra-campaign illumination/phenotype/promotion/budget, không own trọn câu hỏi “search space mới được khai báo ra sao trước protocol lock”.
- **Điểm phản đối**: Tôi không chấp nhận bước nhảy từ “có owner gap” sang “mở ngay Topic 018 umbrella gộp GFS + APE + SSS + CDAP”. Bundle đó gom bốn mechanism còn đang tranh chấp vào cùng một owner quá sớm, đồng thời nở critical path trước khi `017/015/006/013` chốt xong contract nền.
- **Đề xuất sửa**: v1 tiếp tục fold vào topic hiện có với phân vai cứng: `006` = operator grammar + compile-to-manifest; `015` = lineage/state-pack/invalidation; `017` = coverage/cell-elite/surprise/budget; `013` = convergence + diminishing returns; `008` = identity relation. Chỉ mở topic mới nếu sau khi các owner này close vẫn còn một contract giao cắt không thể quy về một owner; nếu phải mở, mở **topic hẹp** kiểu `operator-grammar-and-prelock-ideation-contract`, không mở umbrella `Phase A`.
- **Evidence**: `research/x38/EXECUTION_PLAN.md`; `research/x38/debate/017-epistemic-search-policy/README.md`; `research/x38/docs/search-space-expansion/debate/codex/codex_debate_lan_1.md` (OI-01); `research/x38/docs/search-space-expansion/debate/claude/claude_propone.md` (§5.1 Topic 018); `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_1.md` (OI-01).

### OI-02
- **Stance**: AMEND
- **Điểm đồng ý**: Tôi đồng ý với Claude ở pressure-test “Who writes VDO?” và đồng ý với Codex rằng phải có một contract cho AI/human freedom **trước** protocol lock, thay vì lờ luôn bridge giữa ideation và frozen manifest. Tôi cũng đồng ý với Gemini rằng AI không được có data-test feedback loop xen vào execution.
- **Điểm phản đối**: Tôi bác bỏ `SSS` như **first-class subsystem** của v1. Tôi cũng bác bỏ việc cho lane này nhìn thấy same-dataset ranked results/current registry rồi dùng transcript như audit trail chính; đó là backdoor answer-prior lane, và chính Claude round 1 đã tự chỉ ra tension này.
- **Đề xuất sửa**: bounded ideation lane của v1 phải là **schema-aware, results-blind**. Canonical output chỉ gồm `idea_manifest.jsonl` / `operator_pack.yaml` / `proposal_provenance.json`; transcript hoặc prompt chỉ là supplementary provenance. Lane này không được evaluate, rank, chọn winner, hay inject priors; nó chỉ đề xuất object có thể compile và freeze trước `protocol_freeze.json`.
- **Evidence**: `research/x38/docs/online_vs_offline.md`; `research/x38/debate/003-protocol-engine/findings-under-review.md` (`X38-D-05`); `research/x38/debate/015-artifact-versioning/findings-under-review.md` (`X38-D-14`, `X38-D-17`); `research/x38/docs/search-space-expansion/debate/claude/claude_debate_lan_1.md` (self-critique về SSS); `research/x38/docs/search-space-expansion/debate/codex/codex_debate_lan_1.md` (OI-01, OI-04).

### OI-03
- **Stance**: AMEND
- **Điểm đồng ý**: Tôi giữ lõi v1 theo hướng `Codex + ChatGPT Pro`: lineage, coverage map, cell-elite archive, local probes, surprise triage, equivalence audit, proof bundle, comparison set, phenotype pack, shadow-only memory. Tôi cũng đồng ý với Claude rằng nếu không có cơ chế tạo thêm feature/candidate mới thì framework vẫn bị kẹt ở declared space quá hẹp.
- **Điểm phản đối**: Tôi không đồng ý mang `SSS`, `CDAP`, `GFS depth 2/3`, hay code generation kiểu `APE -> strategy.py` vào core v1. Tôi cũng không đồng ý để “domain-seed + orthogonality” của Gemini trở thành engine chính; nó không giải quyết coverage obligation, per-cell survival, hay proof law.
- **Đề xuất sửa**: minimum viable discovery engine của v1 là: (1) deterministic operator grammar + compile-to-manifest, cho phép **depth-1 grammar enumeration** sau freeze; (2) `feature_lineage` + `candidate_genealogy`; (3) descriptor core + `coverage_map`; (4) `cell_elite_archive`; (5) `local_neighborhood_probes`; (6) `surprise_queue` + `equivalence_audit` + `proof_bundle`; (7) `comparison_set` + `candidate_phenotype` + `epistemic_delta`; (8) descriptor-level `contradiction_registry` shadow-only. Depth-1 chỉ được bật cùng lúc với contract multiplicity control ở `NEW-01`.
- **Evidence**: `research/x38/debate/006-feature-engine/findings-under-review.md` (`X38-D-08`); `research/x38/debate/017-epistemic-search-policy/findings-under-review.md` (`X38-ESP-01`, `X38-ESP-02`); `research/x38/docs/search-space-expansion/debate/codex/codex_debate_lan_1.md` (OI-02, OI-03); `research/x38/docs/search-space-expansion/debate/claude/claude_propone.md` (§6 v1 plan, GFS/APE/SSS); `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_1.md` (OI-03).

### OI-04
- **Stance**: AMEND
- **Điểm đồng ý**: Tôi giữ nguyên kết luận rằng canonical lineage phải là **machine-readable structural lineage** của runner offline; prompt/session ancestry chỉ có giá trị provenance phụ trợ cho bounded ideation lane.
- **Điểm phản đối**: Tôi không đồng ý giữ một artifact lineage “gộp hết” hoặc dùng prompt tree làm authoritative provenance. `Feature formula change` và `candidate role/mutation change` có invalidation semantics khác nhau; nhét chung một nơi làm mờ ranh giới của `015`.
- **Đề xuất sửa**: tách 3 lớp artifact: `feature_lineage.jsonl` (raw channel, transform tree, parent features, parameter slots, compile source, protocol/data hash); `candidate_genealogy.jsonl` (feature IDs, role assignment, threshold mode, mutation parents, architecture relation, protocol/data hash); `proposal_provenance.json` (prompt hash, transcript ref, author type, domain hint ref). Chỉ hai artifact đầu nằm trên replay path; artifact thứ ba là supplementary provenance.
- **Evidence**: `research/x38/debate/006-feature-engine/findings-under-review.md` (`X38-D-08`); `research/x38/debate/015-artifact-versioning/findings-under-review.md` (`X38-D-14`, `X38-D-17`); `research/x38/docs/online_vs_offline.md`; `research/x38/docs/search-space-expansion/debate/codex/codex_debate_lan_1.md` (OI-04); `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_1.md` (OI-04).

### OI-05
- **Stance**: AMEND
- **Điểm đồng ý**: Tôi đồng ý với Codex rằng recognition stack phải có `equivalence audit + proof bundle`, đồng ý với Claude rằng SDL criteria đa chiều có ích như input cho surprise queue, và đồng ý với Gemini rằng semantic recovery có thể tồn tại như lớp giải thích hậu kiểm.
- **Điểm phản đối**: Tôi không chấp nhận `orthogonality + IC` là recognition law chính. Tôi cũng không chấp nhận human causal story trở thành gate bắt buộc ở giữa funnel; machine-verifiable proof phải đi trước. Surprise lane là triage priority, không phải fast-track vào winner lane.
- **Đề xuất sửa**: stack chuẩn cho v1 là `surprise_queue -> equivalence_audit -> proof_bundle -> freeze_comparison_set -> candidate_phenotype -> shadow_registry`. Human chỉ chen vào ở 2 điểm: ambiguity/reconstruction-risk hoặc explanatory note. `semantic_recovery` nếu có thì chỉ chạy **sau proof bundle, sau freeze**, và không có authority trong evidence stack. Surprise criteria tối thiểu phải chứa ít nhất một chiều **không phải peak-score**: decorrelation, plateau width, cost stability, hoặc cross-resolution consistency motif.
- **Evidence**: `research/x38/debate/017-epistemic-search-policy/findings-under-review.md` (`X38-ESP-01`); `research/x38/docs/search-space-expansion/debate/codex/codex_debate_lan_1.md` (OI-03); `research/x38/docs/search-space-expansion/debate/claude/claude_propone.md` (SDL + 3-step validation); `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_propone.md`; `research/x38/docs/search-space-expansion/debate/claude/claude_debate_lan_1.md` (công nhận consistency motif và gate split).

### OI-06
- **Stance**: AMEND
- **Điểm đồng ý**: Tôi đồng ý với Codex/Claude rằng zero-memory là lãng phí evidence, và đồng ý với design brief + Topic 017 rằng same-dataset priors phải shadow-only.
- **Điểm phản đối**: Tôi không ủng hộ `negative_evidence` ở dạng answer-level cấm đoán mơ hồ, và tôi cũng không ủng hộ mang full `EPC`/activation ladder vào core v1 khi `context distance = 0` khiến activation trên same dataset vừa inert vừa dễ thành contamination lane ngụy trang.
- **Đề xuất sửa**: v1 dùng `contradiction_registry.json` ở **descriptor level**, shadow-only, populated từ `proof_bundle` và `contradiction_profile`. Artifact này chỉ chứa descriptor bundle, evidence IDs, contradiction type, locality scope, reconstruction-risk, retention scope, invalidation rule; không chứa feature names/params/winner IDs. Promotion vượt `OBSERVED/REPLICATED_SHADOW` defer; weak signal chỉ được nâng từ “note” sang “shadow prior candidate” khi lặp lại qua session/campaign nhưng vẫn qua reconstruction-risk gate.
- **Evidence**: `research/x38/debate/017-epistemic-search-policy/findings-under-review.md` (`X38-ESP-01`, `X38-ESP-02`, `X38-ESP-03`); `research/x38/docs/design_brief.md`; `research/x38/docs/search-space-expansion/debate/codex/codex_debate_lan_1.md` (OI-05); `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_1.md` (OI-06).

### OI-07
- **Stance**: AGREE
- **Điểm đồng ý**: Tôi giữ nguyên hướng round 1: cross-domain/domain-seed có giá trị **mở bề mặt ideation**, và VDO story cho thấy hoàn toàn có lý do để giữ một hook cho loại input này.
- **Điểm phản đối**: Tôi vẫn không chấp nhận biến domain-seed thành core architecture của v1, và cũng không chấp nhận nhét nó vào canonical operator grammar hay budget law. Thứ thiếu nặng nhất của X38 hiện tại không phải “thiếu cảm hứng”, mà là lineage, coverage, archive, proof, equivalence và gate inventory.
- **Đề xuất sửa**: giữ một hook cực hẹp: `domain_hint_ref` hoặc `cross_domain_seed_ref` trong `proposal_provenance.json`. Hook này không được ảnh hưởng replay semantics, invalidation semantics, hay budget allocation của v1. Nếu tương lai CDAP/domain catalog được mở, nó phải sống ở authoring provenance layer, không sống trong canonical grammar layer.
- **Evidence**: `research/x38/docs/search-space-expansion/debate/gemini/gemini_propone.md`; `research/x38/docs/search-space-expansion/debate/claude/claude_propone.md` (CDAP defer v2); `research/x38/docs/search-space-expansion/debate/codex/codex_debate_lan_1.md` (OI-02); `research/x38/docs/online_vs_offline.md`; `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_1.md` (OI-07).

### OI-08
- **Stance**: AMEND
- **Điểm đồng ý**: Tôi giữ nguyên split ownership `006 / 017 / 013 / 008`, và đồng ý với Codex rằng equivalence không thể bị hạ cấp thành “đổi tên thôi” hay để descriptor-only tự giải quyết.
- **Điểm phản đối**: Tôi không đồng ý tiếp tục để `minimal v1 dimensions` mơ hồ, cũng không đồng ý coi equivalence chỉ là bài toán naming của `008`. Nếu không khóa được descriptor core và common comparison domain, coverage map và proof bundle sẽ vênh nhau.
- **Đề xuất sửa**: `006` owns feature descriptor primitives: `raw_channel_class`, `operator_family`, `transform_depth`, `timeframe_binding`, `threshold_mode_family`. `017` owns strategy cell axes v1: `mechanism_family`, `architecture_depth`, `turnover_bucket`, `holding_bucket`, `timeframe_binding`; còn `complexity_tier`, `cost_elasticity_bucket`, `plateau_bucket`, `regime_logic_flag` là annotations, chưa là cell axes bắt buộc. `013` owns common comparison domain + distance metrics (`paired daily returns`, `top-K overlap`, `rank correlation`, coverage gain). `008` owns identity vocabulary: `SAME_FEATURE`, `SAME_CANDIDATE`, `SAME_PHENOTYPE`, `SAME_SYSTEM_IN_DISGUISE`. Equivalence v1 nên là **hybrid**: descriptor pre-bucket + paired-return distance + nearest-rival / decision-trace audit.
- **Evidence**: `research/x38/debate/006-feature-engine/findings-under-review.md` (`X38-D-08`); `research/x38/debate/017-epistemic-search-policy/README.md`; `research/x38/debate/013-convergence-analysis/findings-under-review.md` (`X38-CA-01`); `research/x38/debate/008-architecture-identity/findings-under-review.md`; `research/x38/docs/search-space-expansion/debate/codex/codex_propone.md` (R2 + G4); `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_1.md` (OI-08).

### NEW-01 — Multiplicity control không thể defer khỏi breadth expansion
- **Lý do mở mới**: `OI-03` và `OI-08` chưa bao phủ đủ câu hỏi “search mở rộng đến đâu trước khi scan-phase correction phải bị khóa thành law”. Round 1 của Codex và Claude đều làm lộ rõ rằng breadth expansion + multiplicity/equivalence control là coupled design, không phải hai workstream độc lập.
- **Đề xuất**: vòng sau phải chốt một contract tối thiểu gồm: (1) common comparison domain; (2) scan-phase correction mode v1 (`FDR`, `cascade`, hoặc hybrid); (3) ranh giới giữa correction ở Stage 3-4 và proof bundle ở Stage 6; (4) invalidation rule khi descriptor taxonomy hoặc common domain đổi. Nếu thiếu contract này, mọi depth-1 grammar expansion đều có risk đẩy false positive vào surprise lane.
- **Evidence**: `research/x38/debate/017-epistemic-search-policy/findings-under-review.md` (`X38-ESP-01`); `research/x38/debate/003-protocol-engine/findings-under-review.md` (`X38-D-05`); `research/x38/debate/013-convergence-analysis/findings-under-review.md` (`X38-CA-01`); `research/x38/docs/search-space-expansion/debate/codex/codex_debate_lan_1.md` (OI-06); `research/x38/docs/search-space-expansion/debate/claude/claude_propone.md` (risk: multiple testing with expanded space).

---

## 5. Per-Agent Critique

### 5.1 Gemini
**Delta vòng 2**: Tôi giữ nguyên đánh giá rằng Gemini đúng ở anti-sandbox và semantic recovery hậu kiểm, nhưng sau round 1 tôi hạ thêm trọng số cho `Prompt Ancestry Tree`: chính proposal và debate của Gemini chưa chứng minh được prompt artifact có replay/invalidation semantics tương xứng với nhu cầu của runner offline. Thứ nên giữ là `domain_hint` như provenance phụ, không phải canonical lineage.

**Evidence**: `research/x38/docs/search-space-expansion/debate/gemini/gemini_propone.md`; `research/x38/docs/search-space-expansion/debate/gemini/gemini_debate_lan_1.md`; `research/x38/debate/015-artifact-versioning/findings-under-review.md` (`X38-D-14`, `X38-D-17`).

### 5.2 Codex
**Delta vòng 2**: Codex vẫn là baseline mạnh nhất. Điểm tăng thêm sau round 1 là Codex đã articulate rất rõ coupling giữa breadth expansion, identity/equivalence, proof bundle và shadow-only memory ceiling. Điểm còn thiếu thật sự của Codex chỉ còn là pre-lock authoring contract vẫn chưa được đóng thành object đủ hẹp.

**Evidence**: `research/x38/docs/search-space-expansion/debate/codex/codex_propone.md`; `research/x38/docs/search-space-expansion/debate/codex/codex_debate_lan_1.md`.

### 5.3 Claude
**Delta vòng 2**: Claude vẫn là pressure-test cần thiết nhất vì buộc cả debate phải trả lời câu hỏi “ai tạo declared space mới?”. Nhưng chính round 1 của Claude cũng đã tự lộ ra hai lỗi thiết kế quan trọng: `SSS` có contamination tension nếu nhìn current registry, và `APE -> generate strategy.py` là bước nhảy quá lạc quan cho v1. Phần đáng lấy của Claude là deterministic slice: depth-1 grammar enumeration, SDL criteria làm queue input, và pressure test về missing owner.

**Evidence**: `research/x38/docs/search-space-expansion/debate/claude/claude_propone.md`; `research/x38/docs/search-space-expansion/debate/claude/claude_debate_lan_1.md`.

### 5.4 ChatGPT Pro
**Delta tự phản biện**: Round 1 của tôi đúng khi ưu tiên `017-first`, gate split, consistency motif và artifact contract; nhưng tôi đã under-specify hai điểm: (1) pre-lock authoring contract cần explicit hơn, không thể chỉ nói “AI ở tầng spec” rồi bỏ lửng bridge; (2) multiplicity control đáng ra phải được kéo lên thành issue riêng ngay từ round 1, thay vì chỉ lẫn trong evidence stack/equivalence discussion.

**Evidence**: `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_propone.md`; `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_1.md`; `research/x38/docs/search-space-expansion/debate/codex/codex_debate_lan_1.md` (OI-06).

---

## 6. Interim Merge Direction

### 6.1 Backbone v1

Backbone v1 tôi sửa từ `Codex + ChatGPT Pro` thành **`Codex + ChatGPT Pro + deterministic slice of Claude`**. “Deterministic slice” ở đây chỉ gồm: grammar-based depth-1 enumeration sau freeze, SDL criteria làm input cho `surprise_queue`, và pressure test “ai viết feature mới”. Tôi tiếp tục loại khỏi backbone: umbrella `Topic 018`, `SSS` first-class subsystem, `CDAP`, `APE` code generation, full `EPC`, và activation ladder vượt `REPLICATED_SHADOW`.

Evidence: `research/x38/docs/search-space-expansion/debate/codex/codex_propone.md`; `research/x38/docs/search-space-expansion/debate/claude/claude_propone.md`; `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_propone.md`; `research/x38/debate/017-epistemic-search-policy/findings-under-review.md` (`X38-ESP-01`, `X38-ESP-02`, `X38-ESP-03`).

### 6.2 Adopt ngay

| # | Artifact / Mechanism | Nguồn | Owner đề xuất |
|---|---------------------|-------|---------------|
| 1 | `bounded_ideation_contract.md` + `proposal_provenance.json` | Claude pressure-test + Codex + ChatGPT Pro | 006 + 015 |
| 2 | `feature_lineage.jsonl` + `candidate_genealogy.jsonl` | Codex + ChatGPT Pro | 015 + 006 |
| 3 | `descriptor_core_v1.md` + `coverage_map.parquet` + `cell_elite_archive.parquet` | ESP-01 + Codex + ChatGPT Pro | 017 + 006 |
| 4 | Deterministic depth-1 grammar enumeration + `local_neighborhood_probes` | Claude + Codex + ChatGPT Pro | 006 + 017 |
| 5 | `surprise_queue.json` + `equivalence_audit` + `proof_bundle/` | Codex + Claude SDL + ChatGPT Pro | 017 + 013 + 008 + 015 |
| 6 | `comparison_set/` + `candidate_phenotype.json` + `epistemic_delta.json` | ESP-01 + ESP-02 + Codex + ChatGPT Pro | 017 + 015 |
| 7 | `contradiction_registry.json` (descriptor-level, shadow-only) | Codex + ChatGPT Pro, constrained by ESP-02/03 | 017 + 015 |

### 6.3 Defer

| # | Artifact / Mechanism | Nguồn | Lý do defer |
|---|---------------------|-------|-------------|
| 1 | Umbrella `Topic 018` kiểu full `Phase A` | Claude | Owner gap là thật, nhưng bundle hiện còn quá rộng so với nhu cầu v1 |
| 2 | `SSS` first-class subsystem | Claude | Bridge đúng nhưng contamination/governance contract chưa đủ chặt |
| 3 | `CDAP` / curated domain catalog là core | Gemini + Claude | Có giá trị ideation, nhưng không sửa critical-path gap của v1 |
| 4 | `APE` code generation + GFS depth 2/3 | Claude | Compute + correctness + multiplicity risk chưa được khóa |
| 5 | Full `EPC` lifecycle + activation ladder vượt `REPLICATED_SHADOW` | Claude + Codex | v1 same-dataset làm activation inert, storage/contract đủ trước |

### 6.4 Ownership tạm

| Topic | Gánh gì |
|-------|---------|
| 006 | Operator grammar, feature descriptor core, compile-to-manifest contract |
| 017 | Coverage obligations, cell archive, surprise/contradiction semantics, phenotype storage scope |
| 015 | Lineage artifacts, proposal provenance, state-pack enumeration, invalidation rules |
| 013 | Common comparison domain, multiplicity correction, convergence/diminishing-returns law |
| 008 | Identity relation taxonomy, equivalence cluster semantics |
| 003 | Insertion points vào Stages 3-8 và freeze law |

---

## 7. Agenda vòng sau

Chỉ bàn các mục sau:
- **OPEN**: `OI-01`, `OI-02`, `OI-03`, `OI-05`, `OI-08`, `NEW-01`
- **PARTIAL, chỉ chốt schema/hook, không bàn lại principle nếu không có bằng chứng mới**: `OI-04`, `OI-06`, `OI-07`

**Format phản hồi cho agent vòng sau:**

```md
### OI-{NN}
- **Stance**: AGREE / DISAGREE / AMEND
- **Điểm đồng ý**: ...
- **Điểm phản đối**: ...
- **Đề xuất sửa**: ...
- **Evidence**: {file path hoặc finding ID}
```

Với `NEW-01`, vòng sau phải trả lời trực diện: breadth expansion có thể triển khai đến mức nào trước khi `scan-phase correction` và `common comparison domain` được khóa thành contract chính thức.

---

## 8. Change Log

| Vòng | Ngày | Agent | Tóm tắt thay đổi |
|------|------|-------|-------------------|
| 1 | 2026-03-25 | chatgptpro | Chọn Codex làm baseline chính, mở 8 OI, khóa 8 CL của round 1. |
| 2 | 2026-03-26 | chatgptpro | Giữ baseline `Codex + ChatGPT Pro`, bác bỏ `SSS/Topic 018` như core v1, bổ sung pre-lock authoring contract, tách feature lineage khỏi candidate genealogy, và mở `NEW-01` về multiplicity control. |

### Status Table

| Issue ID | Trạng thái sau round 2 | Ghi chú |
|----------|------------------------|---------|
| OI-01 | OPEN | Owner gap thật, nhưng chưa đủ bằng chứng cho umbrella topic mới |
| OI-02 | OPEN | Bounded ideation lane chấp nhận được, nhưng contract chi tiết còn mở |
| OI-03 | OPEN | Core v1 đã hẹp lại, nhưng còn tranh chấp về depth-1 enumeration và scope tối thiểu |
| OI-04 | PARTIAL | Principle đã khá rõ; còn chốt schema split và supplementary provenance |
| OI-05 | OPEN | Stack đã rõ hơn, nhưng surprise criteria tối thiểu và human checkpoint còn mở |
| OI-06 | PARTIAL | Memory ceiling đã hẹp lại; còn chốt schema và promotion trigger nội bộ |
| OI-07 | PARTIAL | Domain hint nghiêng mạnh về optional provenance hook |
| OI-08 | OPEN | Ownership split rõ hơn, nhưng minimal v1 dimensions và hybrid equivalence law còn mở |
| NEW-01 | OPEN | Breadth expansion vs multiplicity control phải được khóa thành contract |
