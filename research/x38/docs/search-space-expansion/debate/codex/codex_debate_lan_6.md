---
doc_type: debate_round_review
topic: search-space-expansion
round: 6
author: codex
date: 2026-03-26
status: OPEN
sources:
  - ../../request.md
  - ../../../../docs/online_vs_offline.md
  - ../gemini/gemini_propone.md
  - ../codex/codex_propone.md
  - ../claude/claude_propone.md
  - ../chatgptpro/chatgptpro_propone.md
  - ./codex_debate_lan_5.md
  - ../gemini/gemini_debate_lan_5.md
  - ../gemini/gemini_debate_lan_6.md
  - ../claude/claude_debate_lan_5.md
  - ../claude/claude_debate_lan_6.md
  - ../chatgptpro/chatgptpro_debate_lan_5.md
  - ../../../../debate/003-protocol-engine/findings-under-review.md
  - ../../../../debate/006-feature-engine/findings-under-review.md
  - ../../../../debate/008-architecture-identity/findings-under-review.md
  - ../../../../debate/013-convergence-analysis/findings-under-review.md
  - ../../../../debate/015-artifact-versioning/findings-under-review.md
  - ../../../../debate/017-epistemic-search-policy/findings-under-review.md
  - ../../../../debate/002-contamination-firewall/final-resolution.md
  - ../../../../debate/004-meta-knowledge/final-resolution.md
  - ../../../../debate/007-philosophy-mission/final-resolution.md
  - ../../../../debate/rules.md
  - ../../../../EXECUTION_PLAN.md
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

# Debate Round 6 — Narrowed Interface Closure, Không Tuyên Bố Topic-Wide Termination

## 1. Kết luận nhanh

Codex rời round 6 với kết luận hẹp hơn round 5: `OI-01/02/03/06` có thể rời
active register nếu và chỉ nếu claim được khóa ở mức **architecture/interface
scope**, không overclaim exact field names, exact owner granularity, exact
thresholds, hay exact invalidation tables. `OI-04/05` giữ nguyên `DEFER` vì đó
vẫn là residual đúng owner surface của `015/017`, không phải live dispute của
topic này. Đây **không** phải tuyên bố 4-agent debate đã kết thúc: ChatGPT Pro
chưa có round 6 và `§14b` vẫn cấm Codex tuyên bố topic-wide termination từ một
artifact đơn lẻ (`debate/rules.md` §14b; `../chatgptpro/chatgptpro_debate_lan_5.md`).

---

## 2. Scoreboard

| Agent | Bám yêu cầu | Bám X38 | Khả thi v1 | Sức mở search | Kỷ luật contamination | Độ rõ artifact | Verdict ngắn |
|-------|-------------|---------|------------|---------------|----------------------|----------------|--------------|
| Gemini | Tốt | Tốt | Tốt | Trung bình | Rất tốt | Tốt | Giữ invariant tốt; round 6 rút AST-only là sửa đúng nhất |
| Codex | Tốt | Rất tốt | Tốt | Tốt | Rất tốt | Rất tốt | Kỷ luật boundary/owner tốt nhất; round 5 giữ vài OI lâu hơn cần thiết |
| Claude | Tốt | Tốt | Tốt | Rất tốt | Trung bình | Tốt | Pressure-test mạnh, nhưng round 6 vẫn overclaim vài mapping cụ thể |
| ChatGPT Pro | Rất tốt | Tốt | Tốt | Tốt | Tốt | Rất tốt | Sạch nhất ở split giữa interface closure và downstream residual |

**Giải thích delta round 6**:
- Gemini tăng ở `Độ rõ artifact` vì đã bỏ hẳn AST-only và chấp nhận hybrid/interface framing (`../gemini/gemini_debate_lan_6.md`).
- Claude vẫn có artifact clarity tốt, nhưng Codex không nhận một số mapping cụ thể trong `claude_debate_lan_6.md` là repo-backed ở level topic findings (`../../../../debate/006-feature-engine/findings-under-review.md`; `../../../../debate/013-convergence-analysis/findings-under-review.md`; `../../../../debate/015-artifact-versioning/findings-under-review.md`).

---

## 3. Convergence Ledger

> Round 6 chỉ thêm các điểm Codex chấp nhận sau khi hạ claim về đúng scope.

| ID | Kết luận hội tụ | Basis | Status | Ghi chú |
|----|----------------|-------|--------|---------|
| CL-01 | Promise của framework vẫn là tìm candidate mạnh nhất trong declared search space hoặc kết luận `NO_ROBUST_IMPROVEMENT` | `../../../../debate/007-philosophy-mission/final-resolution.md` | CONVERGED | Imported from CLOSED Topic 007 |
| CL-02 | Same-dataset empirical priors vẫn shadow-only pre-freeze | `../../../../debate/004-meta-knowledge/final-resolution.md` (MK-17) | CONVERGED | Imported from CLOSED Topic 004 |
| CL-03 | Firewall không tự mở category mới cho structural priors; v1 giữ `UNMAPPED + Tier 2 + SHADOW` governance path | `../../../../debate/002-contamination-firewall/final-resolution.md` | CONVERGED | Imported from CLOSED Topic 002 |
| CL-04 | Search-space-expansion chỉ cần khóa **coarse owner split**: `006` = generation/compile surface, `015` = lineage/provenance/invalidation surface, `017` = coverage/archive/surprise surface, `003` = wiring/gating surface. Exact downstream object inventories không được overclaim trong topic này. | `./codex_debate_lan_5.md` (OI-01); `../chatgptpro/chatgptpro_debate_lan_5.md` (OI-01, CL-14); `../claude/claude_debate_lan_6.md` (OI-01, CL-20); `../../../../EXECUTION_PLAN.md`; `../../../../debate/006-feature-engine/findings-under-review.md` (`X38-D-08`); `../../../../debate/015-artifact-versioning/findings-under-review.md` (`X38-D-14`, `X38-D-17`) | CONVERGED | Nếu downstream topic xuất hiện interface không quy được về split này, phải mở `REOPEN-OI-01` với evidence mới |
| CL-05 | `grammar_depth1_seed` là mandatory capability và default cold-start law khi frozen declared registry/seed manifest rỗng; `registry_only` chỉ hợp lệ khi protocol khai báo imported frozen registry/manifest non-empty. Exact validation keys/tests là downstream work của `006/003`. | `./codex_debate_lan_5.md` (OI-02); `../chatgptpro/chatgptpro_debate_lan_5.md` (OI-03, CL-15); `../claude/claude_debate_lan_6.md` (OI-02, CL-20); `../gemini/gemini_debate_lan_6.md` (CL-12); `../../request.md`; `../../../../debate/006-feature-engine/findings-under-review.md` (`X38-D-08`) | CONVERGED | Chốt architecture law, không backfill exact state-machine schema |
| CL-06 | Recognition v1 chỉ cần khóa topology + minimum inventory: `surprise_queue -> equivalence_audit -> proof_bundle -> freeze_comparison_set -> candidate_phenotype -> contradiction_registry`; queue admission cần ít nhất một non-peak-score anomaly axis; proof bundle tối thiểu cần nearest-rival audit, plateau/stability extract, cost sensitivity, một dependency stressor, và contradiction profile. Artifact enumeration/invalidation vẫn chạm `015`. | `./codex_debate_lan_5.md` (OI-03); `../chatgptpro/chatgptpro_debate_lan_5.md` (OI-05, CL-16); `../claude/claude_debate_lan_6.md` (OI-03, CL-20); `../../../../debate/017-epistemic-search-policy/findings-under-review.md` (`X38-ESP-01`, `X38-ESP-02`); `../../../../debate/015-artifact-versioning/findings-under-review.md` (cross-topic tension with 017) | CONVERGED | Exact thresholds/default laws/serialization remain downstream to `017 + 013 + 015` |
| CL-07 | Breadth-expansion chỉ có thể rời local-probe mode khi protocol khai báo đủ **7 required fields**: `descriptor_core_v1`, `common_comparison_domain`, `identity_vocabulary`, `equivalence_method`, `scan_phase_correction_method`, `minimum_robustness_bundle`, `invalidation_scope`. Topic này chỉ khóa **field obligation + anti-AST-only / no-LLM direction**; exact field contents, owner granularity, comparison-domain choice, và invalidation targets vẫn downstream. | `./codex_debate_lan_5.md` (OI-06); `../chatgptpro/chatgptpro_debate_lan_5.md` (OI-08); `../claude/claude_debate_lan_6.md` (OI-06/OI-08 alias); `../gemini/gemini_debate_lan_6.md` (OI-06, CL-10); `../../../../debate/003-protocol-engine/findings-under-review.md` (`X38-D-05`); `../../../../debate/013-convergence-analysis/findings-under-review.md` (`X38-CA-01`); `../../../../debate/015-artifact-versioning/findings-under-review.md` (`X38-D-14`, `X38-D-17`); `../../../../debate/017-epistemic-search-policy/findings-under-review.md` (`X38-ESP-01`, `X38-ESP-02`) | CONVERGED | Codex withdraws the earlier over-routing of candidate-level `identity_vocabulary` to Topic `008`; current x38 evidence does not support that owner claim |

---

## 4. Open Issues Register

### OI-01 — Owner của pre-lock generation lane

- **Stance**: AMEND
- **Điểm đồng ý**: ChatGPT Pro round 5 đánh trúng điểm yếu mạnh nhất của Codex round 5: đợi downstream echo rồi mới route owner là authority-order reversal (`../chatgptpro/chatgptpro_debate_lan_5.md` OI-01; `../../../../EXECUTION_PLAN.md`). Claude round 6 bổ sung object-boundary wording đủ để bác bỏ nỗi lo "owner split chỉ là slogan" ở level architecture (`../claude/claude_debate_lan_6.md` OI-01, CL-20).
- **Điểm phản đối**: Codex **không** chấp nhận overclaim rằng repo đã chốt exact object-by-topic inventories cho `006/015/017/003` ở level findings files. `006`, `003`, và `015` vẫn đang `Open`; topic này chỉ được phép khóa coarse owner surfaces, không được giả vờ downstream object tables đã published (`../../../../debate/006-feature-engine/findings-under-review.md`; `../../../../debate/003-protocol-engine/findings-under-review.md`; `../../../../debate/015-artifact-versioning/findings-under-review.md`).
- **Đề xuất sửa**: Chuyển issue sang `CL-04`. Nếu downstream topic thật sự lộ ra interface không quy được về split coarse này, dùng `REOPEN-OI-01`; không giữ active register chỉ vì downstream chưa viết xong object table của họ.
- **Evidence**: `./codex_debate_lan_5.md` (OI-01); `../chatgptpro/chatgptpro_debate_lan_5.md` (OI-01, CL-14); `../claude/claude_debate_lan_6.md` (OI-01, CL-20); `../../../../EXECUTION_PLAN.md`; `../../../../debate/006-feature-engine/findings-under-review.md` (`X38-D-08`); `../../../../debate/015-artifact-versioning/findings-under-review.md` (`X38-D-14`, `X38-D-17`)
- **Trạng thái**: CONVERGED

### OI-02 — Backbone intra-campaign + producer integration

- **Stance**: AMEND
- **Điểm đồng ý**: Old Codex steel-man của round 5 là hợp lệ: nếu `generation_mode` không có law rõ thì "cold-start default" chỉ là khẩu hiệu. Round 5-6 của ChatGPT Pro, Gemini, và Claude đã trả lời đủ phần architecture: mandatory capability + conditional activation + imported frozen registry exception (`../chatgptpro/chatgptpro_debate_lan_5.md`; `../gemini/gemini_debate_lan_6.md`; `../claude/claude_debate_lan_6.md`).
- **Điểm phản đối**: Codex không nhận phần overreach rằng round 6 đã repo-freeze exact validation fields như `grammar_hash` hay compile checks. Điều đó vẫn là downstream schema/state-machine work của `006/003`, không phải blocker để search-space-expansion rời issue này (`../../../../debate/006-feature-engine/findings-under-review.md`; `../../../../debate/003-protocol-engine/findings-under-review.md`).
- **Đề xuất sửa**: Chuyển issue sang `CL-05`: khóa law ở mức architecture, defer exact validation keys/tests cho downstream topics.
- **Evidence**: `./codex_debate_lan_5.md` (OI-02); `../chatgptpro/chatgptpro_debate_lan_5.md` (OI-03, CL-15); `../claude/claude_debate_lan_6.md` (OI-02); `../gemini/gemini_debate_lan_6.md` (CL-12); `../../request.md`; `../../../../debate/006-feature-engine/findings-under-review.md` (`X38-D-08`)
- **Trạng thái**: CONVERGED

### OI-03 — Surprise lane không được nhầm novelty với value

- **Stance**: AMEND
- **Điểm đồng ý**: Old Codex steel-man cũng đúng ở đây: nếu proof inventory không có object list tối thiểu thì "surprise lane" dễ trượt thành vibe. ChatGPT Pro round 5 đã khóa topology + minimum inventory ở level đủ hẹp; Claude round 6 thêm object wording, và Gemini round 5 đã bỏ yêu cầu freeze threshold tại topic này (`../chatgptpro/chatgptpro_debate_lan_5.md`; `../claude/claude_debate_lan_6.md`; `../gemini/gemini_debate_lan_5.md`).
- **Điểm phản đối**: Codex không chấp nhận owner map bị thu xuống `017 + 013` như thể `015` đã ra khỏi picture. `015` vẫn own artifact enumeration/invalidation cho các ESP artifacts, nên owner surface đúng cho residual downstream là `017 + 013 + 015` (`../../../../debate/015-artifact-versioning/findings-under-review.md`; `../../../../debate/017-epistemic-search-policy/findings-under-review.md`).
- **Đề xuất sửa**: Chuyển issue sang `CL-06`. Khóa topology + minimum proof inventory tại topic này; giao exact thresholds/default comparison law/serialization cho `017 + 013 + 015`.
- **Evidence**: `./codex_debate_lan_5.md` (OI-03, §6.2); `../chatgptpro/chatgptpro_debate_lan_5.md` (OI-05, CL-16); `../claude/claude_debate_lan_6.md` (OI-03); `../../../../debate/017-epistemic-search-policy/findings-under-review.md` (`X38-ESP-01`, `X38-ESP-02`); `../../../../debate/015-artifact-versioning/findings-under-review.md` (cross-topic tension with 017)
- **Trạng thái**: CONVERGED

### OI-06 — Breadth-expansion vs multiplicity/identity/correction coupling

- **Stance**: AMEND
- **Điểm đồng ý**: OI-06 của Codex và OI-08 của Claude/ChatGPT Pro giờ đã cùng nói một chuyện: breadth không được activate nếu protocol chưa khai báo interface bundle đủ cứng. Gemini round 6 rút AST-only; ChatGPT Pro round 5 chấp nhận interface-layer closure; Claude round 6 đưa mapping giúp thấy bundle nào đang được nói tới (`../gemini/gemini_debate_lan_6.md`; `../chatgptpro/chatgptpro_debate_lan_5.md`; `../claude/claude_debate_lan_6.md`).
- **Điểm phản đối**: Codex bác bỏ hai overclaims của peer round 6: (1) nói `7/7 covered` như thể exact field contents và exact comparison-domain choice đã khóa; (2) route candidate-level `identity_vocabulary` sang Topic `008`, trong khi finding `X38-D-13` hiện chỉ nói về protocol/campaign/session identity axes, không phải candidate-equivalence vocabulary (`../../../../debate/008-architecture-identity/findings-under-review.md`). Codex cũng bác bỏ giữ issue `OPEN` chỉ vì exact values/owners chưa frozen; đó là downstream scope, không còn là architecture dispute của topic này.
- **Đề xuất sửa**: Chuyển issue sang `CL-07` với closure hẹp: topic này chỉ khóa 7 required fields phải tồn tại trước breadth activation, cùng với direction "no LLM judge, structural pre-bucket khong du cho final candidate equivalence". Exact field names, exact descriptor axis counts, exact comparison-domain family, exact invalidation targets, và final owner granularity của từng field tiếp tục là downstream work của `003/013/015/017` và tensions liên quan.
- **Evidence**: `./codex_debate_lan_5.md` (OI-06); `../chatgptpro/chatgptpro_debate_lan_5.md` (OI-08); `../claude/claude_debate_lan_6.md` (OI-06/OI-08); `../gemini/gemini_debate_lan_6.md` (OI-06, CL-10); `../../../../debate/003-protocol-engine/findings-under-review.md` (`X38-D-05`); `../../../../debate/013-convergence-analysis/findings-under-review.md` (`X38-CA-01`); `../../../../debate/015-artifact-versioning/findings-under-review.md` (`X38-D-14`, `X38-D-17`); `../../../../debate/017-epistemic-search-policy/findings-under-review.md` (`X38-ESP-01`, `X38-ESP-02`); `../../../../debate/008-architecture-identity/findings-under-review.md` (`X38-D-13`)
- **Trạng thái**: CONVERGED

---

## 5. Per-Agent Critique

### 5.1 Gemini

**Luận điểm lõi**: v1 phải giữ determinism cứng và không quay lại online judge.

**Điểm mạnh**
- Gemini giữ offline/anti-LLM boundary tốt nhất ngay từ đầu, và round 6 rút AST-only đúng lúc để không kéo debate vào false closure (`../gemini/gemini_debate_lan_6.md`; `../../../../docs/online_vs_offline.md`).

**Điểm yếu — phản biện lập luận**
- Gemini round 5 đã thu `breadth_activation_contract` xuống quá hẹp (`common_comparison_domain + identity_vocabulary`). Điểm này chỉ được cứu ở round 6 khi Gemini chấp nhận hybrid/interface framing từ peers (`../gemini/gemini_debate_lan_5.md`; `../gemini/gemini_debate_lan_6.md`).

**Giữ lại**: anti-online discipline; cold-start default; final AST-only retraction.
**Không lấy**: premature closure wording; minimal-bundle overreach của round 5.

### 5.2 Codex

**Luận điểm lõi**: chỉ khóa khi argument cũ đã bị phản bác ở đúng object, không dùng vague consensus.

**Điểm mạnh**
- Round 5 giữ đúng pressure ở `OI-06`; nếu không có 7-field demand thì breadth debate rất dễ trôi về slogan (`./codex_debate_lan_5.md` OI-06).

**Điểm yếu — tự phản biện**
- Codex round 5 đã giữ `OI-01/02/03` lâu hơn cần thiết. Sau ChatGPT Pro round 5 và Claude round 6, phần architecture dispute đã đủ hẹp để rời active register, miễn là không overclaim exact downstream tables (`../chatgptpro/chatgptpro_debate_lan_5.md`; `../claude/claude_debate_lan_6.md`).

**Giữ lại**: anti-false-convergence discipline; 7-field breadth contract.
**Không lấy**: tiếp tục buộc topic này phải đợi downstream object tables mới rời `PARTIAL`.

### 5.3 Claude

**Luận điểm lõi**: pressure-test empty-registry cold-start và ép explicit object wording.

**Điểm mạnh**
- Claude round 6 hữu ích nhất ở chỗ chuyển abstract disagreement thành object wording đủ để Codex test lại steel-man cũ (`../claude/claude_debate_lan_6.md` CL-20).

**Điểm yếu — phản biện lập luận**
- Claude vẫn overclaim vài mapping cụ thể: exact owner granularity, `7/7 covered`, và route sang `008` cho candidate-level identity vocabulary. Những claim đó đi xa hơn repo-backed owner topics hiện có (`../claude/claude_debate_lan_6.md`; `../../../../debate/008-architecture-identity/findings-under-review.md`).

**Giữ lại**: explicit closure wording; conditional cold-start framing.
**Không lấy**: exact 7/7 coverage claim như thể downstream topics đã published those tables.

### 5.4 ChatGPT Pro

**Luận điểm lõi**: khóa interface obligation, rồi đẩy exact law/threshold/invalidation xuống đúng owner topic.

**Điểm mạnh**
- ChatGPT Pro round 5 là artifact sạch nhất cho Codex round 6: authority-order rebuttal ở OI-01, conditional cold-start ở OI-03, và interface-layer closure framing ở OI-08 (`../chatgptpro/chatgptpro_debate_lan_5.md`).

**Điểm yếu — phản biện lập luận**
- Weakness lớn nhất là procedural, không phải technical: ChatGPT Pro chưa có round 6, nên Codex không thể dựa vào artifact của riêng mình để tuyên bố topic-wide termination (`debate/rules.md` §14b).

**Giữ lại**: interface/downstream split; authority-order argument; topology-level closure.
**Không lấy**: bất kỳ cách đọc nào biến Codex round 6 thành global closure.

---

## 6. Interim Merge Direction

### 6.1 Backbone v1

Backbone v1 sau round 6, theo Codex, nên đọc hẹp như sau:

`optional bounded ideation (results-blind, compile-only) -> generation_mode`

- `grammar_depth1_seed` = default cold-start path khi frozen declared registry/seed manifest rỗng
- `registry_only` = chỉ hợp lệ khi protocol khai báo imported frozen registry/manifest non-empty

`-> compile / lineage capture -> descriptor-tagged coverage -> cell-preserving archive -> local probes -> surprise_queue -> equivalence_audit -> proof_bundle -> freeze_comparison_set -> candidate_phenotype -> contradiction_registry (shadow-only) -> epistemic_delta`

`breadth_expansion` chỉ được phép vượt local-probe mode nếu protocol đã khai báo
đủ 7 required fields của `CL-07`. Exact content của từng field không khóa ở đây.

### 6.2 Adopt ngay

| # | Artifact / Mechanism | Nguồn | Owner đề xuất |
|---|---------------------|-------|---------------|
| 1 | `owner_split_contract.md` ở level coarse owner surfaces | CL-04 | 006 + 015 + 017 + 003 |
| 2 | `generation_mode_architecture_note.md` với conditional cold-start law | CL-05 | 006 + 003 |
| 3 | `proof_bundle_minimum_v1.md` ở level topology + minimum inventory | CL-06 | 017 + 013 + 015 |
| 4 | `breadth_activation_contract.md` skeleton với 7 required declared fields | CL-07 | 003 + 013 + 015 + 017 |
| 5 | `feature_lineage.jsonl` + `candidate_genealogy.jsonl` + `proposal_provenance.json` semantic split | OI-04 residual remap từ round 5 | 015 + 006 |
| 6 | `contradiction_registry.json` direction: descriptor-level, shadow-only, no answer-shaped payload | OI-05 residual remap từ round 5 | 017 + 015 |

### 6.3 Defer

| # | Artifact / Mechanism | Nguồn | Lý do defer |
|---|---------------------|-------|-------------|
| 1 | Exact lineage field list + invalidation matrix | OI-04 residual | Thuộc Topic `015`, không còn là live search-space dispute |
| 2 | Exact contradiction row schema, retention, reconstruction-risk handling | OI-05 residual | Thuộc `015 + 017` |
| 3 | Exact `scan_phase_correction_method` default | CL-07 residual | Thuộc `003/013` |
| 4 | Exact descriptor axis counts / axis values / thresholds | CL-07 residual | Thuộc `017` và tensions liên quan với `006` |
| 5 | Exact comparison-domain family + serialization | CL-07 residual | Thuộc `013/015`; topic này chỉ khóa field obligation |
| 6 | Exact invalidation targets khi descriptor/comparison/cost contracts đổi | CL-07 residual | Thuộc `015` |

### 6.4 Ownership tạm

| Topic | Gánh gì |
|-------|---------|
| 006 | Generation/compile surface của feature side, registry/seed import side |
| 015 | Lineage/provenance semantics, artifact enumeration, invalidation tables |
| 017 | Strategy-level descriptors, coverage/archive/surprise/phenotype direction |
| 013 | Comparison/correction/convergence obligations |
| 003 | Stage insertion, gating, activation blockers |

---

## 7. Agenda vòng sau

Không còn agenda round 7 từ phía Codex. Sau round 6, Codex-side active register
đã rỗng ở level architecture/interface của topic này.

Các bước hợp lệ tiếp theo chỉ còn:
- ChatGPT Pro nộp round 6 để giải bất đối xứng `§14b`.
- Hoặc tạo `REOPEN-*` với evidence mới, nếu downstream topic thật sự lộ ra gap
  mà `CL-04..CL-07` không bao phủ.
- Hoặc chuyển sang synthesis / judgment artifact theo workflow hậu debate.

Codex **không** ủng hộ thêm một round 7 debate thường nếu không có `REOPEN-*`
evidence mới (`debate/rules.md` §13, §14).

---

## 8. Change Log

| Vòng | Ngày | Agent | Tóm tắt thay đổi |
|------|------|-------|-------------------|
| 6 | 2026-03-26 | codex | Khóa `OI-01/02/03/06` bằng cách hạ claim về architecture/interface scope, giữ `OI-04/05` ở `DEFER`, sửa owner map của proof artifacts để không làm rơi `015`, và từ chối tuyên bố topic-wide termination khi ChatGPT Pro chưa có round 6 |

**Status Table (required by `debate/rules.md` §11)**

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| OI-01 | Owner của pre-lock generation lane | Judgment call | CONVERGED | "Nếu downstream chưa echo object table của họ thì owner split vẫn chỉ là slogan." | Đúng ở round 5, nhưng không còn đúng sau authority-order rebuttal của ChatGPT Pro và object wording của Claude. Topic này chỉ cần coarse owner split; exact inventories thuộc downstream topics và có thể dùng `REOPEN-*` nếu thật sự lộ gap. |
| OI-02 | Backbone intra-campaign + producer integration | Thiếu sót | CONVERGED | "Exact `generation_mode` validation fields chưa enumerate thì chưa thể đóng." | Sai object ở round 6. Search-space-expansion chỉ cần architecture law: mandatory capability + conditional activation. Exact validation keys/tests là downstream schema work của `006/003`. |
| OI-03 | Surprise lane không được nhầm novelty với value | Thiếu sót | CONVERGED | "Proof inventory chưa xong vì owner map và artifact obligations chưa viết gọn." | Steel-man chỉ còn đúng nếu bỏ sót `015`. Sau khi giữ `017 + 013 + 015` trong downstream owner cluster, architecture dispute đã hết: topic này chỉ cần topology + minimum inventory. |
| OI-04 | Canonical provenance = structural lineage, prompt refs = provenance phụ | Thiếu sót | DEFER | "Field list/invalidation chưa xong nên issue phải ở lại active register." | Sai owner surface: semantic split không còn là live dispute của search-space-expansion; residual belongs to Topic `015`. |
| OI-05 | Cross-campaign memory của v1 dừng ở shadow-only contradiction storage | Judgment call | DEFER | "Row schema/retention chưa close nên memory issue vẫn phải active ở đây." | Sai owner surface: topic này chỉ chốt ceiling-level direction. Row schema, retention, reconstruction-risk, invalidation thuộc `015 + 017`. |
| OI-06 | Breadth-expansion vs multiplicity/identity/correction coupling | Thiếu sót | CONVERGED | "Chưa freeze exact 7-field contents, exact comparison domain, exact invalidation targets, và final owner granularity thì breadth issue chưa thể rời `OPEN`." | Sai scope sau round 6. Topic này chỉ cần khóa field obligation + anti-AST-only/no-LLM direction. Exact field contents, owners, defaults, và invalidation tables là downstream closures của `003/013/015/017`. |
