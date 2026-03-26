---
doc_type: debate_round_review
topic: search-space-expansion
round: 4
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
  - ../gemini/gemini_debate_lan_3.md
  - ./codex_debate_lan_3.md
  - ../claude/claude_debate_lan_3.md
  - ../chatgptpro/chatgptpro_debate_lan_3.md
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
  - ../../../../debate/004-meta-knowledge/final-resolution.md
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

# Debate Round 4 — Khóa Contract Hẹp, Không Backdate Hội Tụ

## 1. Kết luận nhanh

Round 4 của Codex chỉ bàn delta trên 6 OI còn `OPEN/PARTIAL` từ round 3 của
chính Codex. Tôi không reopen các nhánh đã chết (`Topic 018`, `SSS`
first-class, `APE` codegen) vì không có `REOPEN-*` mới đủ chuẩn theo
`debate/rules.md` §12; tranh chấp còn sống chỉ là contract hẹp của pre-lock
producer, cold-start default, minimum surprise/proof inventory, lineage field
split, contradiction storage shape, và bundle multiplicity/equivalence.

Tôi cũng không backdate các `CONVERGED` do peer round 3 đề xuất. `CL-11..CL-14`
theo Claude là hội tụ theo substance, nhưng chưa có đủ steel-man confirmation
theo `debate/rules.md` §7-§9, nên ở round 4 này tôi giữ chúng trong trạng thái
`PARTIAL`/`OPEN` tương ứng. Cuối cùng, tôi remap Gemini theo **substance hiện tại**
chứ không đếm raw OI-ID của Gemini như shared numbering, để tránh false
convergence (`docs/search-space-expansion/debate/gemini/gemini_debate_lan_3.md`;
`docs/search-space-expansion/debate/claude/claude_debate_lan_3.md`).

## 2. Scoreboard

Không đổi scoreboard tổng thể so với round 3. Delta thực chất của round này nằm
ở narrowing contract, không nằm ở đổi ranking giữa các agent.

| Agent | Bám yêu cầu | Bám X38 | Khả thi v1 | Sức mở search | Kỷ luật contamination | Độ rõ artifact | Verdict ngắn |
|-------|-------------|---------|------------|---------------|----------------------|----------------|--------------|
| Gemini | Trung bình | Tốt | Trung bình | Trung bình | Tốt | Yếu | Hữu ích ở anti-online boundary; không đủ để own contract core |
| Codex | Rất tốt | Rất tốt | Tốt | Tốt | Tốt | Rất tốt | Backbone vẫn sạch nhất sau khi ép contract xuống object-level |
| Claude | Tốt | Trung bình | Trung bình | Rất tốt | Trung bình | Tốt | Pressure test cold-start vẫn đúng; baggage round 1 không được quay lại |
| ChatGPT Pro | Rất tốt | Rất tốt | Rất tốt | Tốt | Rất tốt | Rất tốt | Guardrail và owner split tốt nhất; cần chốt exact contract thay vì dừng ở framing |

Evidence: `docs/search-space-expansion/debate/codex/codex_debate_lan_3.md`;
`docs/search-space-expansion/debate/claude/claude_debate_lan_3.md`;
`docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_3.md`;
`docs/search-space-expansion/debate/gemini/gemini_debate_lan_3.md`.

## 3. Convergence Ledger

Không thêm `CL-*` mới ở round 4. Các điểm peer đề xuất hội tụ trong round 3
(`bounded ideation`, `3-artifact lineage split`, `contradiction registry`,
`domain-hint hook`) chỉ được xem là **near-converged substance**, chưa đủ điều
kiện `CONVERGED` của `debate/rules.md` §7-§9 nếu chưa có steel-man confirmation
explicit giữa các agent.

| ID | Kết luận hội tụ | Basis | Status | Ghi chú |
|----|----------------|-------|--------|---------|
| CL-01 | Promise của framework vẫn là tìm candidate mạnh nhất trong declared search space hoặc kết luận `NO_ROBUST_IMPROVEMENT` | `debate/007-philosophy-mission/final-resolution.md` | CONVERGED | Imported from CLOSED Topic 007 |
| CL-02 | Same-dataset empirical priors vẫn shadow-only pre-freeze | `debate/004-meta-knowledge/final-resolution.md` (MK-17) | CONVERGED | Imported from CLOSED Topic 004 |
| CL-03 | Firewall không tự mở category mới cho structural priors; v1 giữ `UNMAPPED + Tier 2 + SHADOW` governance path | `debate/002-contamination-firewall/final-resolution.md` | CONVERGED | Imported from CLOSED Topic 002 |

## 4. Open Issues Register

### OI-01 — Owner của pre-lock generation lane
- **Stance**: AMEND
- **Điểm đồng ý**: Tôi giữ kết luận của round 3 rằng owner gap là có thật: `017` không own pre-lock authoring, và reopen `Topic 018` / `SSS` / `APE` codegen ở round 4 là stale branch, không phải live disagreement (`debate/017-epistemic-search-policy/README.md`; `docs/search-space-expansion/debate/codex/codex_debate_lan_3.md` OI-01; `docs/search-space-expansion/debate/claude/claude_debate_lan_3.md` OI-01; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_3.md` OI-01).
- **Điểm phản đối**: Tôi không chấp nhận coi `006 + 015` đã là ownership decision đóng xong. `X38-D-08` mới own registry pattern; `X38-D-14/X38-D-17` own artifact enumeration + invalidation. Nếu round 4 chỉ lặp câu “fold vào 006/015/017” mà không chỉ ra object boundary thì owner gap vẫn còn nguyên ở dạng trừu tượng.
- **Đề xuất sửa**: Khóa split hẹp ở mức object: `006` own `operator_grammar`, `generation_mode`, `seed_manifest` compilation và admissibility của producer; `015` own `feature_lineage.jsonl`, `candidate_genealogy.jsonl`, `proposal_provenance.json` cùng invalidation table; `017` chỉ own budget/coverage/surprise semantics sau `protocol_lock`; `003` wiring khi upstream close. Giữ `PARTIAL` cho đến khi 006/015 xác nhận boundary này trong topic của chính họ.
- **Evidence**: `debate/006-feature-engine/findings-under-review.md` (X38-D-08); `debate/015-artifact-versioning/findings-under-review.md` (X38-D-14, X38-D-17); `debate/017-epistemic-search-policy/README.md`; `debate/rules.md` §12.

### OI-02 — Backbone intra-campaign + producer integration
- **Stance**: AMEND
- **Điểm đồng ý**: Backbone intra-campaign không đổi: `descriptor tagging -> coverage map -> cell-elite archive -> local probes` là xương sống của `ESP-01`, và producer chỉ nên đi vào backbone này như object đã compile trước lock (`debate/017-epistemic-search-policy/findings-under-review.md` X38-ESP-01; `docs/search-space-expansion/debate/codex/codex_debate_lan_3.md` OI-02).
- **Điểm phản đối**: Tôi không chấp nhận hai cực đoan còn sót lại: (1) `grammar_depth1_seed` chỉ là optional garnish cho cold-start; (2) `grammar_depth1_seed` phải chạy như hard prerequisite cho **mọi** campaign kể cả khi registry đã non-empty và protocol đã cố ý freeze declared universe. Cực (1) bỏ ngỏ cold-start failure mode; cực (2) overread `X38-D-08`, nơi repo hiện đã giả định seeded registry pattern và exhaustive scan trên declared space.
- **Đề xuất sửa**: Khóa `generation_mode` ở mức contract: `grammar_depth1_seed` là **default cold-start path** khi registry rỗng hoặc chưa có seed universe freezeable; `registry_only` chỉ hợp lệ khi protocol đã freeze `stage1_registry.parquet` non-empty; `ideation_assisted_append` là lane bổ sung tùy chọn, không thay default. Giữ `PARTIAL` vì exact operator set, lookback bounds và trigger condition vẫn thuộc 006/003/017.
- **Evidence**: `docs/search-space-expansion/request.md`; `docs/online_vs_offline.md`; `debate/006-feature-engine/findings-under-review.md` (X38-D-08); `debate/017-epistemic-search-policy/findings-under-review.md` (X38-ESP-01); `docs/search-space-expansion/debate/claude/claude_debate_lan_3.md` OI-03; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_3.md` OI-03.

### OI-03 — Surprise lane không được nhầm novelty với value
- **Stance**: AMEND
- **Điểm đồng ý**: Tôi giữ topology đã hẹp lại qua round 2-3: `surprise_queue -> equivalence_audit -> proof_bundle -> comparison_set -> candidate_phenotype`, với surprise chỉ là triage priority và human chỉ chen vào sau machine-verifiable proof hoặc khi có reconstruction-risk / explanation ambiguity (`debate/017-epistemic-search-policy/findings-under-review.md` X38-ESP-01, X38-ESP-02; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_3.md` OI-05).
- **Điểm phản đối**: Tôi không chấp nhận freeze numeric trigger ở round 4 (`corr < 0.3`, `2x plateau`, v.v.) khi `X38-D-05` và `X38-CA-01` vẫn chưa freeze comparison domain + metric. Tôi cũng tiếp tục bác bỏ `corr + IC` kiểu Gemini như primary recognition law; đó là anomaly heuristic, không phải proof law.
- **Đề xuất sửa**: Chốt interface-level minimum cho v1: queue input phải mang ít nhất một anomaly axis **không phải peak-score** trong nhóm {decorrelation, plateau/stability, cost or risk-profile anomaly, cross-resolution consistency, contradiction-resurrection}; proof bundle tối thiểu phải chứa {nearest-rival equivalence trên common comparison domain, plateau/stability extract, cost sensitivity, một dependency test kiểu ablation hoặc split perturbation, contradiction profile nếu candidate đi vào phenotype/shadow lane}. Threshold cụ thể để 017/013/003 chốt downstream.
- **Evidence**: `debate/017-epistemic-search-policy/findings-under-review.md` (X38-ESP-01, X38-ESP-02); `debate/003-protocol-engine/findings-under-review.md` (X38-D-05); `debate/013-convergence-analysis/findings-under-review.md` (X38-CA-01); `docs/search-space-expansion/debate/claude/claude_debate_lan_3.md` OI-05; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_3.md` OI-05.

### OI-04 — Canonical provenance = structural lineage, prompt refs = provenance phụ
- **Stance**: AMEND
- **Điểm đồng ý**: Substance của 3-artifact split đã gần như thẳng hàng: `feature_lineage.jsonl`, `candidate_genealogy.jsonl`, `proposal_provenance.json`; chỉ hai artifact đầu nằm trên replay path, artifact cuối là provenance phụ (`docs/search-space-expansion/debate/codex/codex_debate_lan_3.md` OI-04; `docs/search-space-expansion/debate/claude/claude_debate_lan_3.md` OI-04; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_3.md` OI-04).
- **Điểm phản đối**: Tôi không đồng ý flip issue này sang `CONVERGED` ở round 4, vì `X38-D-14/X38-D-17` vẫn chưa enumerate field list và invalidation cascade đủ cụ thể. Nếu làm vậy, ta sẽ hội tụ ở slogan nhưng bỏ trống đúng phần 015 đang own.
- **Đề xuất sửa**: Khóa semantics tối thiểu theo artifact: `feature_lineage` invalidate downstream candidate/evaluation artifacts khi operator tree, parameter slots, hoặc timeframe binding đổi; `candidate_genealogy` invalidate candidate/evaluation artifacts khi role assignment, mutation parent, threshold family, hoặc architecture template đổi; `proposal_provenance` **không** tự tạo invalidation trên replay path, chỉ phục vụ audit. Giữ `PARTIAL` cho tới khi 015 đưa bảng fields + invalidation triggers.
- **Evidence**: `debate/015-artifact-versioning/findings-under-review.md` (X38-D-14, X38-D-17); `debate/006-feature-engine/findings-under-review.md` (X38-D-08); `docs/online_vs_offline.md`; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_3.md` OI-04.

### OI-05 — Cross-campaign memory của v1 dừng ở shadow-only contradiction storage
- **Stance**: AMEND
- **Điểm đồng ý**: Same-dataset ceiling đã đóng bởi `MK-17`, và hướng descriptor-level `contradiction_registry` shadow-only là live consensus direction; activation vượt shadow hoặc answer-shaped negative memory đều không thuộc v1 (`debate/004-meta-knowledge/final-resolution.md` MK-17, C3; `debate/002-contamination-firewall/final-resolution.md`; `debate/017-epistemic-search-policy/findings-under-review.md` X38-ESP-02, X38-ESP-03).
- **Điểm phản đối**: Tôi không đồng ý backslide sang promotion-ladder debate trong OI này; `ESP-03` đã nói `ACTIVE_STRUCTURAL_PRIOR` và `DEFAULT_METHOD_RULE` inert trong v1. Tôi cũng không đồng ý gọi issue này đã `CONVERGED` khi storage shape, retention scope và invalidation của contradiction rows còn chưa được 015 enumerate.
- **Đề xuất sửa**: Chốt minimal representation cho v1: mỗi row của `contradiction_registry.json` phải gắn vào `phenotype_id` hoặc `descriptor_bundle_hash`, có `evidence_ids`, `contradiction_type`, `locality_scope`, `reconstruction_risk`, `retention_scope`, và `invalidation_scope`; không mang feature names, lookbacks, thresholds, winner IDs. Giữ `PARTIAL` cho đến khi 015/017 chốt storage law và invalidation cascade.
- **Evidence**: `debate/004-meta-knowledge/final-resolution.md` (MK-17, C3); `debate/002-contamination-firewall/final-resolution.md`; `debate/017-epistemic-search-policy/findings-under-review.md` (X38-ESP-02, X38-ESP-03); `docs/search-space-expansion/debate/codex/codex_debate_lan_3.md` OI-05; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_3.md` CL-10.

### OI-06 — Breadth-expansion vs multiplicity/identity/correction coupling
- **Stance**: AMEND
- **Điểm đồng ý**: `NEW-01` của ChatGPT Pro làm rõ đúng điểm còn mở nhất của round 4: breadth producer không thể merge nếu thiếu comparison/correction/equivalence contract. Tôi giữ issue này ở `OPEN` vì đây vẫn là blocker thực chất, không chỉ là detail downstream (`debate/003-protocol-engine/findings-under-review.md` X38-D-05; `debate/013-convergence-analysis/findings-under-review.md` X38-CA-01; `debate/008-architecture-identity/findings-under-review.md` X38-D-13; `debate/017-epistemic-search-policy/findings-under-review.md` X38-ESP-01, X38-ESP-04).
- **Điểm phản đối**: Tôi không chấp nhận hai đường tắt đang cạnh tranh nhau: (1) freeze exact law quá sớm (`Holm` default, `corr >= 0.85`, fixed cell counts) như thể 003/013 đã close; (2) hạ equivalence xuống static AST-hash / Euclidean-only law như thể identity của candidate có thể đọc hết từ code structure. `X38-D-13` và `X38-CA-01` đều cho thấy identity/convergence là multi-axis object, không phải chỉ naming hay source hash.
- **Đề xuất sửa**: Giữ `OPEN`, nhưng khóa interface bundle bắt buộc trước khi breadth producer vượt local probes hiện hữu: `descriptor_core_v1`, `common_comparison_domain`, `identity_vocabulary`, `scan_phase_correction_method`, `minimum_robustness_bundle`, `invalidation_scope`. Direction tạm cho v1: comparison domain ở candidate level nên là paired daily returns trên shared evaluation window sau cost model; structural hash/parameter distance chỉ là helper ở feature-level, không đủ làm final candidate equivalence law. Exact correction default (`Holm`/`FDR`/`cascade`) vẫn để 003/013 chốt.
- **Evidence**: `debate/003-protocol-engine/findings-under-review.md` (X38-D-05); `debate/013-convergence-analysis/findings-under-review.md` (X38-CA-01); `debate/008-architecture-identity/findings-under-review.md` (X38-D-13); `debate/017-epistemic-search-policy/findings-under-review.md` (X38-ESP-01, X38-ESP-04); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_3.md` NEW-01; `docs/search-space-expansion/debate/claude/claude_debate_lan_3.md` OI-08.

## 5. Per-Agent Critique

Không mở critique card mới ở round 4. Mọi delta phản biện cần thiết đã được hấp
thụ trực tiếp vào `OI-01..OI-06` để tránh relitigate landscape cũ và tránh vi
phạm delta-only rule của `DEBATE_FORMAT.md` / `debate/rules.md`.

## 6. Interim Merge Direction

### 6.1 Backbone v1

Backbone v1 nên được đọc hẹp hơn round 3 như sau:

`optional bounded ideation (results-blind, compile-only) -> generation_mode`

- `grammar_depth1_seed` = default cold-start path
- `registry_only` = chỉ hợp lệ khi declared universe đã non-empty và frozen
- `ideation_assisted_append` = optional additive lane

`-> protocol lock -> descriptor tagging -> coverage_map -> cell_elite_archive -> local_probes -> surprise_queue -> equivalence_audit -> proof_bundle -> comparison_set -> candidate_phenotype -> contradiction_registry (shadow-only) -> epistemic_delta`

### 6.2 Adopt ngay

| # | Artifact / Mechanism | Nguồn | Owner đề xuất |
|---|---------------------|-------|---------------|
| 1 | `pre_lock_authoring_contract` với split 006/015/017 | Codex round 3 + ChatGPT Pro round 3 + Claude pressure test | 006 + 015 + 017 |
| 2 | `generation_mode` contract với `grammar_depth1_seed` làm default cold-start path | Claude round 3 + ChatGPT Pro round 3 + request cold-start gap | 006 |
| 3 | `feature_lineage.jsonl` + `candidate_genealogy.jsonl` + `proposal_provenance.json` | Codex + Claude + ChatGPT Pro | 015 + 006 |
| 4 | `descriptor_core_v1` + `coverage_map` + `cell_elite_archive` + `local_probes` | X38-ESP-01 + Codex + ChatGPT Pro | 017 + 006 + 003 |
| 5 | `surprise_queue` + minimum `proof_bundle` inventory + `comparison_set` | Codex + Claude SDL slice + ChatGPT Pro | 017 + 013 + 015 |
| 6 | `contradiction_registry.json` descriptor-level, shadow-only | MK-17 ceiling + Codex + ChatGPT Pro | 017 + 015 |
| 7 | Interface bundle cho breadth (`comparison_domain`, `correction_method`, `identity_vocabulary`, `invalidation_scope`) | NEW-01 pressure from ChatGPT Pro | 013 + 015 + 017 + 008 |

### 6.3 Defer

| # | Artifact / Mechanism | Nguồn | Lý do defer |
|---|---------------------|-------|-------------|
| 1 | `Topic 018` / umbrella `Phase A` | Earlier Claude / earlier Codex option | Dead branch trong session này; không có `REOPEN-*` mới |
| 2 | `SSS` first-class subsystem | Earlier Claude | Dead branch sau round 2-3; bounded ideation lane đã thay thế |
| 3 | `GFS depth 2/3`, `APE` code generation, GA/continuous mutation | Claude + Gemini | Compute/correctness/multiplicity contract chưa khóa |
| 4 | `CDAP` / domain catalog như core architecture | Gemini + Claude | Optional ideation feedstock, không phải critical-path v1 |
| 5 | Activation ladder vượt `REPLICATED_SHADOW` | Codex + Claude | `MK-17` + `ESP-03` làm v1 same-dataset activation inert |
| 6 | Exact correction formula, exact cell counts, exact thresholds | ChatGPT Pro + Claude + Gemini | 003/013/017/008 chưa freeze law đủ để close ở round 4 |

### 6.4 Ownership tạm

| Topic | Gánh gì |
|-------|---------|
| 006 | Operator grammar, feature DSL, generation modes, default cold-start seed producer, feature descriptor primitives |
| 015 | Lineage/provenance artifacts, compile-batch provenance, invalidation tables |
| 017 | Coverage obligations, cell archive, local probes, surprise semantics, phenotype/contradiction shadow storage |
| 013 | Common comparison domain, correction law, convergence/diminishing-returns obligations |
| 008 | Identity vocabulary và equivalence category semantics |
| 003 | Stage insertion points, required artifacts, freeze law wiring |

## 7. Agenda vòng sau

Chỉ tiếp tục 6 OI của Codex còn `OPEN/PARTIAL`. Không reopen `Topic 018`,
`SSS`, hay `APE` codegen nếu không có `REOPEN-*` với evidence mới.

### OI-01
- **Stance**: AMEND
- **Điểm đồng ý**: Owner gap thật; 017 không own pre-lock lane.
- **Điểm phản đối**: “Fold vào 006/015” vẫn chưa đủ nếu không chốt object boundary.
- **Đề xuất sửa**: 006 own producer semantics; 015 own lineage/provenance/invalidation; 017 own post-lock policy.
- **Evidence**: `debate/006-feature-engine/findings-under-review.md`; `debate/015-artifact-versioning/findings-under-review.md`; `debate/017-epistemic-search-policy/README.md`

### OI-02
- **Stance**: AMEND
- **Điểm đồng ý**: `grammar_depth1_seed` nên là default cold-start path.
- **Điểm phản đối**: Không nên biến depth-1 thành universal hard prerequisite cho mọi non-empty registry campaign.
- **Đề xuất sửa**: Chốt `generation_mode` với điều kiện kích hoạt rõ cho `grammar_depth1_seed` vs `registry_only`.
- **Evidence**: `docs/search-space-expansion/request.md`; `debate/006-feature-engine/findings-under-review.md`; `debate/017-epistemic-search-policy/findings-under-review.md`

### OI-03
- **Stance**: AMEND
- **Điểm đồng ý**: Surprise = triage, không phải winner privilege.
- **Điểm phản đối**: Không freeze threshold cụ thể trước khi comparison/correction contract được chốt.
- **Đề xuất sửa**: Khóa minimum anomaly axes + proof-bundle inventory ở mức interface.
- **Evidence**: `debate/017-epistemic-search-policy/findings-under-review.md`; `debate/003-protocol-engine/findings-under-review.md`; `debate/013-convergence-analysis/findings-under-review.md`

### OI-04
- **Stance**: AMEND
- **Điểm đồng ý**: 3-artifact split là direction đúng.
- **Điểm phản đối**: Chưa thể `CONVERGED` nếu 015 chưa chốt fields và invalidation cascade.
- **Đề xuất sửa**: Chốt replay-path semantics của 2 artifact đầu, provenance-only semantics của artifact thứ ba.
- **Evidence**: `debate/015-artifact-versioning/findings-under-review.md`; `docs/online_vs_offline.md`

### OI-05
- **Stance**: AMEND
- **Điểm đồng ý**: Descriptor-level contradiction storage, shadow-only, no activation beyond shadow in v1.
- **Điểm phản đối**: Không reopen promotion ladder; không đóng issue khi storage shape còn mở.
- **Đề xuất sửa**: Chốt row-level fields tối thiểu cho `contradiction_registry.json`.
- **Evidence**: `debate/004-meta-knowledge/final-resolution.md`; `debate/002-contamination-firewall/final-resolution.md`; `debate/017-epistemic-search-policy/findings-under-review.md`

### OI-06
- **Stance**: AMEND
- **Điểm đồng ý**: Breadth-expansion và multiplicity/equivalence control là coupled design.
- **Điểm phản đối**: AST-hash-only hoặc exact `Holm` default đều đang đi trước evidence freeze của 003/013/008.
- **Đề xuất sửa**: Khóa interface bundle trước; exact formula để downstream topics chốt.
- **Evidence**: `debate/003-protocol-engine/findings-under-review.md`; `debate/013-convergence-analysis/findings-under-review.md`; `debate/008-architecture-identity/findings-under-review.md`

## 8. Change Log

| Vòng | Ngày | Agent | Tóm tắt thay đổi |
|------|------|-------|-------------------|
| 1 | 2026-03-25 | codex | Chọn `017-first backbone`, mở 6 OI về owner, backbone, surprise, lineage, memory, multiplicity |
| 2 | 2026-03-26 | codex | Thu hẹp v1 theo bounded pre-lock ideation, structural lineage canonical, cell-elite backbone, shadow-only memory |
| 3 | 2026-03-26 | codex | Chấp nhận producer-gap pressure test nhưng bác bỏ online-first packaging; đề xuất `pre_lock_authoring_contract`, narrow deterministic depth-1 producer, 3-artifact lineage split |
| 4 | 2026-03-26 | codex | Giữ delta-only trên 6 OI; khóa `generation_mode` theo cold-start default thay vì hard universal prerequisite; siết object boundary cho pre-lock owner split; giữ multiplicity/equivalence bundle ở trạng thái `OPEN` cho tới khi 003/013/008 freeze contract |

**Status Table (required by `debate/rules.md` §11)**

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| OI-01 | Owner của pre-lock generation lane | Judgment call | PARTIAL | “Có owner gap nên cần topic umbrella riêng” | Burden of proof cho topic mới chưa đạt; split 006/015/017 giải được phần contract còn sống |
| OI-02 | Backbone intra-campaign + producer integration | Thiếu sót | PARTIAL | “Depth-1 phải là hard prerequisite cho mọi campaign” | Cold-start default là đúng; universal prerequisite overreads X38-D-08 và declared-universe promise |
| OI-03 | Surprise lane không được nhầm novelty với value | Thiếu sót | PARTIAL | “Có thể khóa threshold ngay từ round debate này” | Comparison domain + correction/equivalence contract chưa close ở 003/013/017 |
| OI-04 | Canonical provenance = structural lineage, prompt refs = provenance phụ | Thiếu sót | PARTIAL | “3-artifact split đã đủ để gọi converged” | 015 vẫn chưa enumerate exact fields và invalidation cascade |
| OI-05 | Cross-campaign memory của v1 dừng ở shadow-only contradiction storage | Judgment call | PARTIAL | “Shadow-only ceiling đã đóng thì storage shape không còn quan trọng” | 015/017 vẫn phải chốt row shape, retention và invalidation của contradiction storage |
| OI-06 | Breadth-expansion vs multiplicity/identity/correction coupling | Thiếu sót | OPEN | “Chỉ cần breadth trước, correction để topic sau” | Không có comparison/correction/equivalence contract thì breadth producer đẩy false positives vào archive/surprise lane |
