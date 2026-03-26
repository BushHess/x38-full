---
doc_type: debate_round_review
topic: search-space-expansion
round: 5
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
  - ../gemini/gemini_debate_lan_4.md
  - ./codex_debate_lan_4.md
  - ../claude/claude_debate_lan_4.md
  - ../chatgptpro/chatgptpro_debate_lan_4.md
  - ../gemini/gemini_debate_lan_5.md
  - ../../../online_vs_offline.md
  - ../../../design_brief.md
  - ../../../../AGENTS.md
  - ../../../../x38_RULES.md
  - ../../../../debate/rules.md
  - ../../../../debate/prompt_template.md
  - ../../../../debate/003-protocol-engine/findings-under-review.md
  - ../../../../debate/006-feature-engine/findings-under-review.md
  - ../../../../debate/008-architecture-identity/findings-under-review.md
  - ../../../../debate/013-convergence-analysis/findings-under-review.md
  - ../../../../debate/015-artifact-versioning/findings-under-review.md
  - ../../../../debate/017-epistemic-search-policy/README.md
  - ../../../../debate/017-epistemic-search-policy/findings-under-review.md
  - ../../../../debate/004-meta-knowledge/final-resolution.md
  - ../../../../debate/002-contamination-firewall/final-resolution.md
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

# Debate Round 5 — Khóa Delta Thật, Đẩy Residual Đúng Owner

## 1. Kết luận nhanh

Gemini round 5 hữu ích vì đã bỏ gần hết dead branches và chấp nhận hướng hẹp
`Codex + ChatGPT Pro` cho owner split, conditional cold-start, và
obligation-level proof inventory
(`docs/search-space-expansion/debate/gemini/gemini_debate_lan_5.md`;
`docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md`;
`docs/search-space-expansion/debate/claude/claude_debate_lan_4.md`).

Nhưng Codex không chấp nhận tuyên bố "full convergence". Theo
`debate/rules.md` §7, bare `AGREE` không đủ để backdate `CONVERGED`, và theo
§14b debate cũng chưa thể đóng khi Gemini đã nộp round 5 còn Codex/Claude/
ChatGPT Pro chưa phản hồi round tương ứng
(`debate/rules.md` §7, §14b;
`docs/search-space-expansion/debate/gemini/gemini_debate_lan_5.md`).

Delta thật của round 5 là:
- `OI-01`, `OI-02`, `OI-03` đã hẹp mạnh nhưng vẫn chỉ nên giữ ở `PARTIAL`
  vì còn thiếu trace hội tụ đúng chuẩn và còn residual object/trigger wiring do
  topic owners downstream nắm.
- `OI-04` và `OI-05` không còn là active search-space disputes; chúng nên rời
  active register dưới dạng `DEFER`, vì phần còn lại thuộc `015/017`.
- `OI-06` vẫn là battle thật. Gemini thu bundle xuống
  `common_comparison_domain + identity_vocabulary`, nhưng peer round 4 và các
  findings mở vẫn yêu cầu rộng hơn: `descriptor_core_v1`,
  `equivalence_method`, `scan_phase_correction_method`,
  `minimum_robustness_bundle`, và `invalidation_scope`
  (`docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` OI-06;
  `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md`
  CL-13, NEW-01;
  `docs/search-space-expansion/debate/claude/claude_debate_lan_4.md` OI-08;
  `debate/003-protocol-engine/findings-under-review.md` X38-D-05;
  `debate/013-convergence-analysis/findings-under-review.md` X38-CA-01;
  `debate/008-architecture-identity/findings-under-review.md` X38-D-13).

## 2. Scoreboard

Delta của round 5 không nằm ở đổi baseline, mà ở việc tách đúng đâu là
architecture direction, đâu là downstream residual, và đâu là false closure.

| Agent | Bám yêu cầu | Bám X38 | Khả thi v1 | Sức mở search | Kỷ luật contamination | Độ rõ artifact | Verdict ngắn |
|-------|-------------|---------|------------|---------------|----------------------|----------------|--------------|
| Gemini | Tốt | Tốt | Tốt | Tốt | Rất tốt | Trung bình | Tiếp thu boundary tốt hơn, nhưng đóng quá sớm ở `OI-01..06`, đặc biệt `OI-06` |
| Codex | Rất tốt | Rất tốt | Rất tốt | Tốt | Rất tốt | Rất tốt | Giữ boundary khó nhất ở `OI-06`; sửa `OI-04/05` sang `DEFER` thay vì relitigate |
| Claude | Tốt | Tốt | Tốt | Rất tốt | Tốt | Tốt | Pressure test cold-start và owner split vẫn có giá trị; vẫn đếm convergence nhanh hơn mức an toàn |
| ChatGPT Pro | Rất tốt | Rất tốt | Rất tốt | Tốt | Rất tốt | Rất tốt | Mạnh nhất ở chỗ tách `CL` kiến trúc khỏi `DEFER` downstream và giữ bundle interface đầy đủ |

Evidence: `docs/search-space-expansion/debate/gemini/gemini_debate_lan_5.md`;
`docs/search-space-expansion/debate/codex/codex_debate_lan_4.md`;
`docs/search-space-expansion/debate/claude/claude_debate_lan_4.md`;
`docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md`.

## 3. Convergence Ledger

Không thêm `CL-*` mới ở round 5. Lý do không phải landscape rộng ra, mà vì
Gemini round 5 chưa đi qua chuỗi `steel-man -> rebuttal -> confirmation` đúng
chuẩn `debate/rules.md` §7; do đó Codex chỉ remap trạng thái `OI` theo owner
surface, không backdate `CONVERGED`.

| ID | Kết luận hội tụ | Basis | Status | Ghi chú |
|----|----------------|-------|--------|---------|
| CL-01 | Promise của framework vẫn là tìm candidate mạnh nhất trong declared search space hoặc kết luận `NO_ROBUST_IMPROVEMENT` | `debate/007-philosophy-mission/final-resolution.md` | CONVERGED | Imported from CLOSED Topic 007 |
| CL-02 | Same-dataset empirical priors vẫn shadow-only pre-freeze | `debate/004-meta-knowledge/final-resolution.md` (MK-17) | CONVERGED | Imported from CLOSED Topic 004 |
| CL-03 | Firewall không tự mở category mới cho structural priors; v1 giữ `UNMAPPED + Tier 2 + SHADOW` governance path | `debate/002-contamination-firewall/final-resolution.md` | CONVERGED | Imported from CLOSED Topic 002 |

## 4. Open Issues Register

### OI-01 — Owner của pre-lock generation lane
- **Stance**: AMEND
- **Điểm đồng ý**: Architecture-level split của Gemini round 5 đi đúng hướng: `006` producer/compile, `015` lineage/provenance/invalidation, `017` post-lock coverage/archive/surprise semantics, `003` wiring. ChatGPT Pro round 4 và Claude round 4 cũng đang nhìn cùng object này (`docs/search-space-expansion/debate/gemini/gemini_debate_lan_5.md`; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` OI-01; `docs/search-space-expansion/debate/claude/claude_debate_lan_4.md` OI-01).
- **Điểm phản đối**: Gemini đóng issue quá sớm. Steel-man vị trí cũ của Codex là: nếu `X38-D-08`, `X38-D-14`, `X38-D-17` còn `Open`, thì owner split mới dừng ở slogan. Steel-man này yếu đi rõ rệt, nhưng chưa chết hoàn toàn theo chuẩn `§7`, vì round 5 hiện vẫn thiếu confirmation trace đúng luật và `006/015` chưa tự xác nhận closure wording ở topic của chính họ (`debate/006-feature-engine/findings-under-review.md` X38-D-08; `debate/015-artifact-versioning/findings-under-review.md` X38-D-14, X38-D-17; `debate/rules.md` §7).
- **Đề xuất sửa**: Giữ `PARTIAL`. Khóa direction ở mức topic này: file/CLI owner là downstream implementation, không phải blocker kiến trúc. Round sau, nếu còn tồn tại, chỉ còn được bàn closure wording tối thiểu để `006/015/017/003` tự xác nhận boundary.
- **Evidence**: `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` OI-01; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` OI-01; `docs/search-space-expansion/debate/gemini/gemini_debate_lan_5.md`; `debate/017-epistemic-search-policy/README.md`; `debate/rules.md` §7
- **Trạng thái**: PARTIAL

### OI-02 — Backbone intra-campaign + producer integration
- **Stance**: AMEND
- **Điểm đồng ý**: Gemini round 5 đã bỏ hai cực đoan cũ và chấp nhận đúng law hẹp hơn: `grammar_depth1_seed` là default cold-start path khi registry/seed manifest rỗng; `registry_only` chỉ hợp lệ khi declared universe đã non-empty và frozen (`docs/search-space-expansion/debate/gemini/gemini_debate_lan_5.md`; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` OI-03; `docs/search-space-expansion/debate/claude/claude_debate_lan_4.md` CL-15).
- **Điểm phản đối**: Steel-man vị trí cũ của Codex là: exact `generation_mode` validation fields, `grammar_hash`-style freshness test, operator scope, và wiring vẫn chưa được đóng nên chưa thể gọi `CONVERGED`. Steel-man này vẫn đứng được ở mức rules/completion, vì những fields đó còn nằm đúng owner surface của `006/003/017`, và Gemini round 5 không giải quyết phần đó (`debate/006-feature-engine/findings-under-review.md` X38-D-08; `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` OI-02).
- **Đề xuất sửa**: Giữ `PARTIAL`. Không relitigate mandatory-vs-optional nữa; round sau chỉ còn được bàn exact validation object của `generation_mode`.
- **Evidence**: `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` OI-02; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` OI-03; `docs/search-space-expansion/debate/claude/claude_debate_lan_4.md` CL-15; `debate/006-feature-engine/findings-under-review.md` X38-D-08
- **Trạng thái**: PARTIAL

### OI-03 — Surprise lane không được nhầm novelty với value
- **Stance**: AMEND
- **Điểm đồng ý**: Gemini round 5 đúng khi rút yêu cầu freeze numeric thresholds tại topic này và chấp nhận proof inventory ở mức obligation-level. ChatGPT Pro round 4 cũng nói rõ inventory obligation và numeric threshold là hai tầng khác nhau (`docs/search-space-expansion/debate/gemini/gemini_debate_lan_5.md`; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` OI-05).
- **Điểm phản đối**: Steel-man vị trí cũ của Codex là: nếu `comparison_domain`, correction/equivalence contract, và downstream threshold ownership ở `003/013/017` còn mở, thì chưa thể gọi `CONVERGED`. Steel-man này vẫn đủ mạnh để giữ issue ở `PARTIAL`, vì inventory object đã hẹp nhưng chưa đi qua confirmation trace đúng chuẩn và vẫn còn phụ thuộc rõ vào downstream topic owners (`debate/003-protocol-engine/findings-under-review.md` X38-D-05; `debate/013-convergence-analysis/findings-under-review.md` X38-CA-01; `debate/017-epistemic-search-policy/findings-under-review.md` X38-ESP-01, X38-ESP-02).
- **Đề xuất sửa**: Giữ `PARTIAL`. Round sau, nếu có, chỉ được bàn tên object tối thiểu của proof inventory và cách tách chúng khỏi numeric threshold/default comparison law.
- **Evidence**: `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` OI-03; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` OI-05; `debate/017-epistemic-search-policy/findings-under-review.md` X38-ESP-01, X38-ESP-02; `debate/003-protocol-engine/findings-under-review.md` X38-D-05; `debate/013-convergence-analysis/findings-under-review.md` X38-CA-01
- **Trạng thái**: PARTIAL

### OI-04 — Canonical provenance = structural lineage, prompt refs = provenance phụ
- **Stance**: AMEND
- **Điểm đồng ý**: Gemini đúng ở semantic direction: `feature_lineage` + `candidate_genealogy` nằm trên replay path, còn `proposal_provenance` chỉ là provenance phụ. Đây không còn là live architectural disagreement trong topic này (`docs/search-space-expansion/debate/gemini/gemini_debate_lan_5.md`; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` OI-04; `docs/search-space-expansion/debate/claude/claude_debate_lan_4.md` OI-04).
- **Điểm phản đối**: Gemini vẫn gọi trọn `OI-04` là `CONVERGED`, nhưng phần còn lại nằm đúng ở `015`: field list, invalidation matrix, state-pack enumeration. Giữ issue active ở topic này là stale relitigation; gọi nó đã xong trọn gói cũng là overreach (`debate/015-artifact-versioning/findings-under-review.md` X38-D-14, X38-D-17).
- **Đề xuất sửa**: Chuyển `OI-04` sang `DEFER`. Search-space-expansion không bàn thêm field enumeration/invalidation của `015` nếu không có `REOPEN-*` với evidence mới.
- **Evidence**: `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` OI-04; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` OI-04; `debate/015-artifact-versioning/findings-under-review.md` X38-D-14, X38-D-17
- **Trạng thái**: DEFER

### OI-05 — Cross-campaign memory của v1 dừng ở shadow-only contradiction storage
- **Stance**: AMEND
- **Điểm đồng ý**: Gemini đúng ở ceiling-level: same-dataset contradiction memory của v1 phải descriptor-level, shadow-only, không activate vượt shadow. Điểm này đã bám MK-17 từ trước (`docs/search-space-expansion/debate/gemini/gemini_debate_lan_5.md`; `debate/004-meta-knowledge/final-resolution.md` MK-17; `debate/017-epistemic-search-policy/findings-under-review.md` X38-ESP-03).
- **Điểm phản đối**: Gemini đóng quá tay ở row schema. `phenotype_id + evidence_ids + contradiction_type` không đủ để trả lời reconstruction-risk, retention, locality scope, invalidation scope, hay forbidden-payload pressure đang nằm ở `ESP-02/03` và `015`. Giữ issue active ở đây là sai owner surface; gọi nó đã chốt trọn cũng sai object (`debate/017-epistemic-search-policy/findings-under-review.md` X38-ESP-02, X38-ESP-03; `debate/015-artifact-versioning/findings-under-review.md` cross-topic tension với 017).
- **Đề xuất sửa**: Chuyển `OI-05` sang `DEFER`. Topic này chốt ceiling; `015 + 017` tiếp quản row schema, retention, reconstruction-risk handling, và invalidation.
- **Evidence**: `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` OI-05; `debate/017-epistemic-search-policy/findings-under-review.md` X38-ESP-02, X38-ESP-03; `debate/015-artifact-versioning/findings-under-review.md` X38-D-14, X38-D-17; `debate/004-meta-knowledge/final-resolution.md` MK-17
- **Trạng thái**: DEFER

### OI-06 — Breadth-expansion vs multiplicity/identity/correction coupling
- **Stance**: AMEND
- **Điểm đồng ý**: Gemini đúng ở principle-level: breadth producer không thể merge nếu thiếu identity/comparison contract. Claude round 4 và ChatGPT Pro round 4 cũng đồng ý đúng điểm này (`docs/search-space-expansion/debate/gemini/gemini_debate_lan_5.md`; `docs/search-space-expansion/debate/claude/claude_debate_lan_4.md` OI-08; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` CL-13).
- **Điểm phản đối**: Gemini thu bundle xuống quá hẹp. Peer round 4 và open findings vẫn yêu cầu ít nhất các surfaces sau: `descriptor_core_v1`, `common_comparison_domain`, `identity_vocabulary`, `equivalence_method`, `scan_phase_correction_method`, `minimum_robustness_bundle`, và `invalidation_scope`. Chỉ nêu `common_comparison_domain + identity_vocabulary` không đủ để breadth vượt local probes mà không đẩy false positives vào archive/surprise lane (`docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` OI-06; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` CL-13, OI-08, NEW-01; `docs/search-space-expansion/debate/claude/claude_debate_lan_4.md` OI-08).
- **Đề xuất sửa**: Giữ `OPEN`. Nếu round 6 tồn tại, topic này chỉ còn được bàn đúng một câu hỏi: complete `breadth_activation_contract` bundle tối thiểu là gì trước khi breadth vượt local probes.
- **Evidence**: `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` OI-06; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` CL-13, OI-08, NEW-01; `docs/search-space-expansion/debate/claude/claude_debate_lan_4.md` OI-08; `debate/003-protocol-engine/findings-under-review.md` X38-D-05; `debate/013-convergence-analysis/findings-under-review.md` X38-CA-01; `debate/008-architecture-identity/findings-under-review.md` X38-D-13
- **Trạng thái**: OPEN

## 5. Per-Agent Critique

### 5.1 Gemini

**Luận điểm lõi**: Round 5 nên đóng topic và handover sang spec.

**Điểm mạnh**
- Gemini cuối cùng đã bỏ phần lớn stale branches và chấp nhận đúng 3 sửa quan trọng: owner split, conditional cold-start law, và obligation-level proof inventory (`docs/search-space-expansion/debate/gemini/gemini_debate_lan_5.md`).

**Điểm yếu — phản biện lập luận**
- Gemini vẫn đóng quá sớm. Lỗi không nằm ở conclusion “đã hẹp lại”, mà ở argument: `AGREE + Không còn` không đủ cho `CONVERGED` theo `debate/rules.md` §7, và `OI-06` vẫn bị thu hẹp bundle quá mức so với peer round 4 và findings mở của `003/013/008`.

**Giữ lại**: anti-online discipline; acceptance of owner split; conditional cold-start; proof inventory without frozen thresholds.
**Không lấy**: full-closure claim; 3-field contradiction row; 2-field breadth bundle.

### 5.2 Codex

**Luận điểm lõi**: chỉ khóa những gì đã đủ contract-level evidence, không backdate convergence.

**Điểm mạnh**
- Round 4 giữ đúng pressure ở `OI-06` và không để breadth vượt interface bundle (`docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` OI-06).

**Điểm yếu — tự phản biện**
- Round 4 đã quá sticky ở `OI-04/05`. Sau ChatGPT Pro round 4, framing đúng hơn không phải giữ `PARTIAL`, mà là remap chúng sang `DEFER` vì phần còn lại đã đúng owner surface của `015/017`.

**Giữ lại**: strictness on OI-06; refusal to freeze exact correction law too early.
**Không lấy**: tiếp tục giữ `OI-04/05` ở active register.

### 5.3 Claude

**Luận điểm lõi**: cold-start generation và interface obligations phải được trả lời rõ.

**Điểm mạnh**
- Claude round 4 vẫn đúng ở pressure test cold-start và owner split; OI-08 của Claude cũng phân biệt đúng giữa interface-layer convergence và exact-law defer (`docs/search-space-expansion/debate/claude/claude_debate_lan_4.md` OI-08).

**Điểm yếu — phản biện lập luận**
- Claude vẫn có xu hướng đếm `CONVERGED` nhanh hơn mức an toàn; đặc biệt ở các CL mới của round 4, closure language đi trước `§7(c)` confirmation.

**Giữ lại**: conditional cold-start; owner split; interface-vs-exact-law split.
**Không lấy**: over-counted closure language.

### 5.4 ChatGPT Pro

**Luận điểm lõi**: tách đúng contract kiến trúc khỏi downstream implementation/residual law.

**Điểm mạnh**
- ChatGPT Pro round 4 là tài liệu tốt nhất cho boundary `CL vs DEFER`: semantic lineage split và breadth coupling principle được khóa, nhưng field matrix / exact correction default / invalidation cascade không bị giả vờ là xong (`docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` OI-04, OI-08, NEW-01).

**Điểm yếu — phản biện lập luận**
- ChatGPT Pro vẫn giữ `OI-01/03` ở `PARTIAL` thêm một vòng vì wording thận trọng. Codex round 5 không đi xa hơn ở status, nhưng lấy đúng lesson từ GPT: tách active issue khỏi downstream residual.

**Giữ lại**: architecture-level/defer split; full breadth bundle requirements; conditional cold-start law.
**Không lấy**: anything that suggests only two fields are enough for OI-06 closure.

## 6. Interim Merge Direction

### 6.1 Backbone v1

Backbone v1 sau round 5 nên đọc như sau:

`optional bounded ideation (results-blind, compile-only) -> generation_mode`

- `grammar_depth1_seed` = default khi registry/seed manifest rỗng
- `registry_only` = chỉ hợp lệ khi declared registry đã frozen non-empty
- `ideation_assisted_append` = lane bổ sung, không thay default

`-> compile_manifest -> feature_lineage / candidate_genealogy / proposal_provenance -> descriptor_tagging -> coverage_map -> cell_elite_archive -> local_probes -> surprise_queue -> equivalence_audit -> proof_bundle -> freeze_comparison_set -> candidate_phenotype -> contradiction_registry (descriptor-level, shadow-only) -> epistemic_delta`

Breadth mechanism vẫn **bị block** nếu chưa có `breadth_activation_contract`
đủ bundle: `descriptor_core_v1`, `common_comparison_domain`,
`identity_vocabulary`, `equivalence_method`, `scan_phase_correction_method`,
`minimum_robustness_bundle`, và `invalidation_scope`.

### 6.2 Adopt ngay

| # | Artifact / Mechanism | Nguồn | Owner đề xuất |
|---|---------------------|-------|---------------|
| 1 | Direction-level owner split `006/015/017/003` | OI-01 narrowed consensus | 006 + 015 + 017 + 003 |
| 2 | `generation_mode` skeleton với conditional cold-start law | OI-02 narrowed consensus | 006 + 003 + 017 |
| 3 | `proof_bundle_minimum_v1` + anomaly-axis gate ở mức obligation | OI-03 narrowed consensus | 017 + 013 + 015 |
| 4 | `feature_lineage.jsonl` + `candidate_genealogy.jsonl` + `proposal_provenance.json` semantic split | OI-04 remap | 015 + 006 |
| 5 | `contradiction_registry.json` direction: descriptor-level, shadow-only, no answer-shaped payload | OI-05 remap | 017 + 015 |
| 6 | `breadth_activation_contract.md` skeleton với 7 required fields | OI-06 residual | 013 + 017 + 008 + 003 + 015 |

### 6.3 Defer

| # | Artifact / Mechanism | Nguồn | Lý do defer |
|---|---------------------|-------|-------------|
| 1 | Exact field list + invalidation matrix của lineage artifacts | OI-04 residual | Thuộc Topic `015`, không còn là live search-space dispute |
| 2 | Exact row schema, retention, reconstruction-risk handling, invalidation scope của `contradiction_registry.json` | OI-05 residual | Thuộc `015 + 017`; topic này chỉ chốt direction, không chốt final row shape |
| 3 | Exact correction default (`Holm` / `FDR` / `cascade`) | OI-06 residual | `003/013` còn `Open`; topic này chỉ chốt interface obligation |
| 4 | Exact descriptor/cell axes values và thresholds | OI-06 residual | `017/013/008` own exact parameterization |
| 5 | Physical script / CLI / file-path mapping cho owners | Gemini critique branch | Downstream implementation, không phải architecture issue của topic này |
| 6 | `GFS depth 2/3`, `APE` code generation, GA/continuous mutation | earlier Claude/Gemini asks | Ngoài compute/correctness budget của v1 |

### 6.4 Ownership tạm

| Topic | Gánh gì |
|-------|---------|
| 006 | Operator grammar, feature DSL, generation modes, seed-manifest compilation, feature descriptor primitives |
| 015 | Lineage/provenance semantics, artifact enumeration, invalidation tables |
| 017 | Coverage obligations, cell archive, local probes, surprise semantics, phenotype/contradiction storage direction |
| 013 | Common comparison domain, convergence/correction obligations, robustness bundle requirements |
| 008 | Identity vocabulary và equivalence category boundary |
| 003 | Stage insertion points, freeze/gating wiring, breadth activation blocker |

## 7. Agenda vòng sau

Không reopen `OI-04` hoặc `OI-05` nếu không có `REOPEN-*` với evidence mới.
Nếu round 6 tồn tại, active register chỉ còn 4 items đáng bàn:

### OI-01
- **Stance**: AMEND
- **Điểm đồng ý**: Architecture split đã aligned.
- **Điểm phản đối**: Còn thiếu closure wording đủ chuẩn `§7` để rời `PARTIAL`.
- **Đề xuất sửa**: Chốt exactly what 006/015/017/003 need to echo in their own topics.
- **Evidence**: `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` OI-01; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` OI-01; `debate/rules.md` §7

### OI-02
- **Stance**: AMEND
- **Điểm đồng ý**: Conditional cold-start law đã aligned.
- **Điểm phản đối**: Exact `generation_mode` validation fields vẫn chưa được enumerate.
- **Đề xuất sửa**: Chốt minimal state-machine fields: registry non-empty test, freshness/hash test, and owner boundary.
- **Evidence**: `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` OI-02; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` OI-03

### OI-03
- **Stance**: AMEND
- **Điểm đồng ý**: Obligation-level proof inventory đã aligned.
- **Điểm phản đối**: Mapping giữa queue/proof objects và downstream comparison/correction owners vẫn chưa được viết gọn.
- **Đề xuất sửa**: Chốt object list đủ hẹp cho `proof_bundle_minimum_v1`, không bàn threshold/default law nữa.
- **Evidence**: `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` OI-03; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` OI-05

### OI-06
- **Stance**: AMEND
- **Điểm đồng ý**: Coupling principle đã chốt; breadth không thể đi một mình.
- **Điểm phản đối**: Bundle blocker của Gemini R5 vẫn thiếu `descriptor_core_v1`, `equivalence_method`, `scan_phase_correction_method`, `minimum_robustness_bundle`, và `invalidation_scope`.
- **Đề xuất sửa**: Chốt complete `breadth_activation_contract` rồi mới cho issue rời `OPEN`.
- **Evidence**: `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` CL-13, NEW-01; `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` OI-06; `docs/search-space-expansion/debate/claude/claude_debate_lan_4.md` OI-08

## 8. Change Log

| Vòng | Ngày | Agent | Tóm tắt thay đổi |
|------|------|-------|-------------------|
| 5 | 2026-03-26 | codex | Giữ `OI-01/02/03` ở `PARTIAL`, remap `OI-04/05` sang `DEFER`, và giữ `OI-06` ở `OPEN` vì Gemini R5 thu hẹp breadth bundle quá mức so với peer round 4 và open findings |

**Status Table (required by `debate/rules.md` §11)**

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| OI-01 | Owner của pre-lock generation lane | Judgment call | PARTIAL | “Architecture-level split đã aligned đủ để gọi converged ngay.” | Chưa qua chuỗi `§7` đầy đủ và 006/015/017/003 chưa echo closure wording trong owner surface của chính họ. |
| OI-02 | Backbone intra-campaign + producer integration | Thiếu sót | PARTIAL | “Conditional cold-start law đã rõ nên issue này đóng được ngay.” | Exact `generation_mode` validation fields, freshness test, và owner boundary vẫn là downstream work chưa được enumerate. |
| OI-03 | Surprise lane không được nhầm novelty với value | Thiếu sót | PARTIAL | “Obligation-level inventory đủ để đóng mà không cần threshold.” | Direction đã hẹp mạnh, nhưng object mapping sang comparison/correction owners vẫn chưa được viết gọn và chưa qua `§7` confirmation trace. |
| OI-04 | Canonical provenance = structural lineage, prompt refs = provenance phụ | Thiếu sót | DEFER | “Vì field list/invalidation chưa xong nên issue phải ở lại active register.” | Sai owner surface: semantic split không còn là live search-space dispute; residual belongs to Topic `015`. |
| OI-05 | Cross-campaign memory của v1 dừng ở shadow-only contradiction storage | Judgment call | DEFER | “Vì row schema chưa close nên memory issue phải ở lại active register.” | Sai owner surface: ceiling đã hẹp đủ, còn row shape/retention/reconstruction/invalidation là artifact-contract work của `015/017`. |
| OI-06 | Breadth-expansion vs multiplicity/identity/correction coupling | Thiếu sót | OPEN | “`common_comparison_domain` + `identity_vocabulary` đã đủ để close breadth coupling.” | Peer round 4 và open findings vẫn yêu cầu thêm correction, robustness, equivalence, descriptor, và invalidation surfaces trước breadth activation. |
