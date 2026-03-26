---
doc_type: debate_round_review
topic: search-space-expansion
round: 7
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
  - ../gemini/gemini_debate_lan_3.md
  - ../codex/codex_debate_lan_3.md
  - ../claude/claude_debate_lan_3.md
  - ./chatgptpro_debate_lan_3.md
  - ../gemini/gemini_debate_lan_4.md
  - ../codex/codex_debate_lan_4.md
  - ../claude/claude_debate_lan_4.md
  - ./chatgptpro_debate_lan_4.md
  - ../gemini/gemini_debate_lan_5.md
  - ../codex/codex_debate_lan_5.md
  - ../claude/claude_debate_lan_5.md
  - ./chatgptpro_debate_lan_5.md
  - ../gemini/gemini_debate_lan_6.md
  - ../codex/codex_debate_lan_6.md
  - ../claude/claude_debate_lan_6.md
  - ./chatgptpro_debate_lan_6.md
  - ../../../online_vs_offline.md
  - ../../../design_brief.md
  - ../../../../AGENTS.md
  - ../../../../x38_RULES.md
  - ../../../../EXECUTION_PLAN.md
  - ../../../../debate/rules.md
  - ../../../../debate/prompt_template.md
  - ../../../../debate/003-protocol-engine/findings-under-review.md
  - ../../../../debate/006-feature-engine/findings-under-review.md
  - ../../../../debate/008-architecture-identity/findings-under-review.md
  - ../../../../debate/013-convergence-analysis/findings-under-review.md
  - ../../../../debate/015-artifact-versioning/findings-under-review.md
  - ../../../../debate/017-epistemic-search-policy/findings-under-review.md
  - ../../../../debate/017-epistemic-search-policy/README.md
  - ../../../../debate/002-contamination-firewall/final-resolution.md
  - ../../../../debate/004-meta-knowledge/final-resolution.md
  - ../../../../debate/007-philosophy-mission/final-resolution.md
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

# Debate Round 7 — Xác nhận điều kiện dừng và bàn giao sang synthesis

## 1. Kết luận nhanh

Round 7 không mở thêm delta kiến trúc. Delta thật duy nhất sau khi đồng bộ raw từ GitHub là procedural: caveat `§14b` mà Codex ghi ở round 6 đã hết hiệu lực vì `chatgptpro_debate_lan_6.md` nay đã hiện diện trong working set cùng với ba peer round-6 files còn lại. Khi blocker bất đối xứng này biến mất, active register của topic cũng rỗng: `OI-01/02/03/06/08` đã `CONVERGED`, `OI-04/05` đã `DEFER` đúng owner surface, và `OI-07` đã `CONVERGED` từ các vòng trước mà không có `REOPEN-*` mới. **Evidence**: `docs/search-space-expansion/debate/codex/codex_debate_lan_6.md` §1, Status Table; `docs/search-space-expansion/debate/gemini/gemini_debate_lan_6.md` §4, §7; `docs/search-space-expansion/debate/claude/claude_debate_lan_6.md` Status Table; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_6.md` Status Table; `debate/rules.md` §13-§14b.

Tôi không tạo `REOPEN-*` hay `NEW-*` ở round này, vì sync repo không đưa ra bằng chứng kiến trúc mới phủ định `CL-01..CL-20` hay làm lộ owner gap mới. Kéo topic này sang round 8 sẽ chỉ lặp lại ledger đã khóa và vi phạm tinh thần `debate/rules.md`: khi tranh chấp thực chất đã hết, topic phải chuyển sang closure artifact rồi bàn giao cho synthesis/downstream owners, không được giữ mở bằng paperwork. **Evidence**: `debate/rules.md` §7, §13, §14; `docs/search-space-expansion/debate/codex/codex_debate_lan_6.md` Status Table; `docs/search-space-expansion/debate/claude/claude_debate_lan_6.md` Status Table; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_6.md` Status Table.

Verdict cuối: debate kết thúc ở round 7. Convergence Ledger của round 6 cộng với delta termination ở round 7 là đủ để chuyển chủ đề này sang self-contained synthesis theo `final-resolution.md`, còn các residual đã `DEFER` phải được route sang đúng topic owner thay vì ngồi lại trong `search-space-expansion`. **Evidence**: `docs/search-space-expansion/debate/gemini/gemini_debate_lan_6.md` §7; `docs/search-space-expansion/debate/codex/codex_debate_lan_6.md` §1; `docs/search-space-expansion/debate/claude/claude_debate_lan_6.md` §1, Status Table; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_6.md` §1, Status Table.

---

## 2. Scoreboard

Không có thay đổi substantive so với round 6. Delta duy nhất là cột verdict cuối cùng giờ chuyển từ “đủ để đóng từ phía agent này” sang “đã đủ để đóng ở mức 4-agent debate” vì điều kiện đối xứng `§14b` đã được thỏa. **Evidence**: `docs/search-space-expansion/debate/codex/codex_debate_lan_6.md` §1; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_6.md`.

| Agent | Bám yêu cầu | Bám X38 | Khả thi v1 | Sức mở search | Kỷ luật contamination | Độ rõ artifact | Verdict ngắn |
|-------|-------------|---------|------------|---------------|----------------------|----------------|--------------|
| Gemini | Tốt | Tốt | Tốt | Tốt | Rất tốt | Tốt | Chốt đúng ở vòng cuối khi rút `AST-only` và chấp nhận hybrid equivalence. |
| Codex | Rất tốt | Rất tốt | Rất tốt | Tốt | Rất tốt | Rất tốt | Boundary-setter tốt nhất; blocker procedural `§14b` mà Codex giữ ở round 6 nay đã được giải quyết. |
| Claude | Tốt | Tốt | Rất tốt | Rất tốt | Tốt | Rất tốt | Closure artifact mạnh nhất cho battle cuối, đặc biệt ở `CL-19/CL-20` và reconciliation table. |
| ChatGPT Pro | Rất tốt | Rất tốt | Rất tốt | Tốt | Rất tốt | Rất tốt | Tách rõ interface closure khỏi downstream residue và tự sửa đúng lúc ở `OI-08`. |

**Evidence**: `docs/search-space-expansion/debate/gemini/gemini_debate_lan_6.md`; `docs/search-space-expansion/debate/codex/codex_debate_lan_6.md`; `docs/search-space-expansion/debate/claude/claude_debate_lan_6.md`; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_6.md`.

---

## 3. Convergence Ledger

`CL-01..CL-20` giữ nguyên từ `chatgptpro_debate_lan_6.md`. Round 7 chỉ thêm delta termination để khóa điều kiện dừng của topic.

| ID | Kết luận hội tụ | Basis | Status | Ghi chú |
|---|---|---|---|---|
| CL-21 | Điều kiện dừng của topic đã được thỏa ở mức 4-agent debate: sau khi round 6 của cả bốn agent đều hiện diện, không còn `OI-*` nào ở trạng thái `OPEN/PARTIAL`; topic chuyển từ debate sang synthesis, và chỉ được quay lại bằng `REOPEN-*` nếu xuất hiện bằng chứng repo mới phủ định các `CL` đã khóa. | `debate/rules.md` §13-§14b; `docs/search-space-expansion/debate/gemini/gemini_debate_lan_6.md` §4, §7; `docs/search-space-expansion/debate/codex/codex_debate_lan_6.md` §1, Status Table; `docs/search-space-expansion/debate/claude/claude_debate_lan_6.md` Status Table; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_6.md` Status Table | CONVERGED | Round 7 là termination artifact, không phải vòng tranh luận kiến trúc mới. |

---

## 4. Open Issues Register

Active register = ∅.

Không còn `OI-*` nào ở trạng thái `OPEN` hoặc `PARTIAL`. `OI-01/02/03/06/08` đã `CONVERGED`; `OI-04/05` đã `DEFER` đúng owner surface; `OI-07` đã `CONVERGED` từ round 4/5 và không có bằng chứng mới để `REOPEN-*`. Vì vậy round 7 không phản hồi thêm issue nào theo format `### OI-{NN}` — đơn giản vì không còn issue mở hợp lệ để phản hồi. **Evidence**: `docs/search-space-expansion/debate/gemini/gemini_debate_lan_6.md` §4, §7; `docs/search-space-expansion/debate/codex/codex_debate_lan_6.md` Status Table; `docs/search-space-expansion/debate/claude/claude_debate_lan_6.md` Status Table; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_6.md` Status Table; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` (`CL-11`, `OI-07`).

---

## 5. Per-Agent Critique

### 5.1 Gemini

**Luận điểm lõi**: giữ biên offline cực cứng; breadth chỉ hợp lệ khi deterministic và không có online leak.

**Điểm mạnh**
- Gemini sửa đúng disagreement substantive cuối cùng khi rút `AST-only` và chấp nhận hybrid equivalence ở round 6. Không có bước sửa này thì topic không thể đóng sạch ở `OI-06/OI-08`. **Evidence**: `docs/search-space-expansion/debate/gemini/gemini_debate_lan_6.md` (`CL-10`, `OI-06`).

**Điểm yếu — phản biện lập luận**
- Lập luận sai của Gemini không nằm ở kết luận “phải deterministic”, mà ở argument round 5 rằng bundle breadth chỉ cần quá ít field và topic đã “full convergence”. Hai lập luận này đều thiếu object boundary và đã bị chính round 6 của Gemini rút lại. **Evidence**: `docs/search-space-expansion/debate/gemini/gemini_debate_lan_5.md`; `docs/search-space-expansion/debate/gemini/gemini_debate_lan_6.md`; `docs/search-space-expansion/debate/codex/codex_debate_lan_5.md` (`OI-06`).

**Giữ lại**: anti-online boundary; determinism discipline; willingness to drop wrong `AST-only` position.

**Không lấy**: breadth shorthand hai-field; premature closure wording ở round 5.

### 5.2 Codex

**Luận điểm lõi**: không được fake-close một coupled contract bằng ngôn ngữ mềm; owner split và breadth activation phải explicit ở interface layer.

**Điểm mạnh**
- Codex đóng vai boundary-setter tốt nhất của toàn debate. `OI-06` round 5 là object clarification quan trọng nhất cho battle cuối vì nó ép mọi agent phải nói rõ breadth activation cần những surfaces nào thay vì nói “để owner topic tự lo”. **Evidence**: `docs/search-space-expansion/debate/codex/codex_debate_lan_5.md` (`OI-06`); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_6.md` (`CL-20`).

**Điểm yếu — phản biện lập luận**
- Argument yếu của Codex là đồng nhất hóa “downstream chưa echo closure wording” với “architecture chưa hội tụ”. Điều đó đúng như một pressure test ở round 5, nhưng không còn đúng sau khi owner split và validation boundaries đã explicit. Giữ `PARTIAL` vô hạn theo logic này sẽ phá authority order và làm topic upstream lệ thuộc vào downstream paperwork. **Evidence**: `docs/search-space-expansion/debate/codex/codex_debate_lan_5.md` (`OI-01/02/03`); `docs/search-space-expansion/debate/codex/codex_debate_lan_6.md` §1, Status Table; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_6.md` (`CL-17`, `OI-01/02/03`); `debate/rules.md` §14.

**Giữ lại**: 7-field breadth-activation contract; anti-false-convergence discipline; coarse owner split at architecture layer.

**Không lấy**: downstream-echo as prerequisite for upstream convergence.

### 5.3 Claude

**Luận điểm lõi**: nếu interface đã đủ rõ, exact law phải defer đúng owner thay vì kéo topic tiếp tục tranh luận.

**Điểm mạnh**
- Claude tạo ra closure artifact mạnh nhất cho OI cuối cùng: reconciliation giữa `CL-19` và Codex bundle làm rõ cái gì là required declaration field, cái gì là downstream value table. Đây là nước đi giúp chuyển debate từ “còn tranh chấp” sang “đủ để synthesis”. **Evidence**: `docs/search-space-expansion/debate/claude/claude_debate_lan_5.md` (`CL-19`); `docs/search-space-expansion/debate/claude/claude_debate_lan_6.md` (`CL-19`, `CL-20`, Status Table).

**Điểm yếu — phản biện lập luận**
- Yếu điểm của Claude không phải kết luận closure, mà ở argument procedural: một số đoạn round 5 dùng `§7(c)` hơi rộng tay, như thể silence sau hai vòng tự nó đủ thành confirmation. Điều đó không đủ; thứ thật sự khóa issue là peer artifacts ở round 6 và symmetry `§14b`, không phải silence. **Evidence**: `docs/search-space-expansion/debate/claude/claude_debate_lan_5.md`; `docs/search-space-expansion/debate/codex/codex_debate_lan_6.md` §1; `debate/rules.md` §7(c), §14b.

**Giữ lại**: interface-vs-downstream split; reconciled CL-19/20 closure artifact.

**Không lấy**: silence-based reading của `§7(c)` như cơ chế closure đủ mạnh một mình.

### 5.4 ChatGPT Pro

**Luận điểm lõi**: search-space-expansion chỉ nên khóa architecture contract; exact schema/default/threshold tables phải route về owner topic đúng chỗ.

**Điểm mạnh**
- Điểm đúng nhất của ChatGPT Pro là tách dứt điểm “interface obligation” khỏi “exact downstream law”. Nhờ vậy `OI-08` cuối cùng được đóng sạch mà không cướp scope của `013/015/017/008/006/003`. **Evidence**: `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` (`CL-13`, `OI-08`); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_5.md` (`CL-14..CL-16`, `OI-08`); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_6.md` (`CL-17..CL-20`).

**Điểm yếu — tự phản biện**
- Yếu điểm của chính tôi là giữ `OI-08` mở thêm một vòng sau khi Codex round 5 đã đưa ra đúng 7-field bundle còn thiếu. Round 6 đã sửa điều đó, nhưng vẫn là một vòng trễ do tôi quá thận trọng ở chỗ không cần thiết. **Evidence**: `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_5.md` (`OI-08`); `docs/search-space-expansion/debate/codex/codex_debate_lan_5.md` (`OI-06`); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_6.md` (`CL-20`).

**Giữ lại**: owner split discipline; conditional cold-start law; proof-side recognition stack; interface/downstream separation.

**Không lấy**: extra caution ở `OI-08` sau khi Codex bundle đã đủ rõ.

---

## 6. Interim Merge Direction

### 6.1 Backbone v1

Backbone cuối cùng để mang sang synthesis là:

`optional bounded_ideation (results-blind, compile-only, provenance-only) -> generation_mode {grammar_depth1_seed default when frozen seed registry/manifest is empty; registry_only only when imported manifest is frozen, non-empty, compatible} -> protocol_lock -> descriptor_core_v1 -> coverage_map / cell_archive / local_probes -> surprise_queue -> equivalence_audit -> proof_bundle -> freeze_comparison_set -> candidate_phenotype -> contradiction_registry (shadow-only) -> epistemic_delta`

Breadth-expansion không được rời local-probe/archive mode cho đến khi protocol khai báo đủ breadth-activation contract v1. Exact schema/default law/threshold tables không sống ở topic này nữa. **Evidence**: `docs/design_brief.md`; `docs/online_vs_offline.md`; `debate/006-feature-engine/findings-under-review.md` (`X38-D-08`); `debate/017-epistemic-search-policy/findings-under-review.md` (`X38-ESP-01`, `X38-ESP-02`); `docs/search-space-expansion/debate/codex/codex_debate_lan_6.md` (`CL-04..CL-07`); `docs/search-space-expansion/debate/claude/claude_debate_lan_6.md` (`CL-19`, `CL-20`); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_6.md` (`CL-17..CL-20`).

### 6.2 Adopt ngay

| # | Artifact / Mechanism | Nguồn | Owner đề xuất |
|---|---------------------|-------|---------------|
| 1 | `coarse_owner_split_v1` (`006` generate/compile; `015` lineage/provenance/invalidation; `017` coverage/archive/surprise; `003` wiring/gating) | `CL-17`; Codex `CL-04`; Claude `CL-20` | 006 / 015 / 017 / 003 |
| 2 | `generation_mode` law: `grammar_depth1_seed` default cold-start, `registry_only` conditional path | `CL-18`; Codex `CL-05`; Gemini `CL-12` | 006 + 003 |
| 3 | `recognition_stack_minimum_v1` (`surprise_queue -> equivalence_audit -> proof_bundle -> freeze_comparison_set -> candidate_phenotype -> contradiction_registry`) | `CL-19`; Codex `CL-06`; Claude `CL-17` | 017 + 013 + 015 + 003 |
| 4 | `breadth_activation_contract_v1` với 7 required fields: `descriptor_core_v1`, `common_comparison_domain`, `identity_vocabulary`, `equivalence_method`, `scan_phase_correction_method`, `minimum_robustness_bundle`, `invalidation_scope` | `CL-20`; Codex `CL-07`; Claude `CL-19` | 003 + 013 + 008 + 015 + 017 |
| 5 | `hybrid_equivalence_contract_v1` = deterministic structural pre-bucket + behavioral nearest-rival audit trên common comparison domain | Gemini `CL-10`; Claude `CL-19`; ChatGPT Pro `CL-20` | 008 + 013 + 017 |
| 6 | `domain_hint_ref` / cross-domain seed chỉ là optional provenance hook, không có replay/control-law semantics | `chatgptpro_debate_lan_4.md` (`CL-11`); Claude `CL-12` | 015 |

### 6.3 Defer

| # | Artifact / Mechanism | Nguồn | Lý do defer |
|---|---------------------|-------|-------------|
| 1 | Exact serialized field list + validation keys cho `generation_mode` | `CL-18`; Codex `CL-05` | Thuộc schema/wiring detail của `006/003`, không còn là architecture dispute |
| 2 | Field enumeration cho `feature_lineage` / `candidate_genealogy` / `proposal_provenance` và invalidation matrix đầy đủ | `OI-04` residual; `015` findings (`X38-D-14`, `X38-D-17`) | Thuộc Topic `015` |
| 3 | Contradiction row schema, retention, reconstruction-risk handling | `OI-05` residual | Thuộc Topic `015/017` |
| 4 | Exact `scan_phase_correction_method` default, exact correction thresholds, exact anomaly thresholds | `NEW-01` residual; `013` findings (`X38-CA-01`) | Thuộc Topic `013/017` |
| 5 | Exact identity taxonomy, exact equivalence categories, exact invalidation targets triggered by taxonomy/domain/cost-model change | `CL-20` residual; `008` findings (`X38-D-13`); `015` findings (`X38-D-17`) | Thuộc Topic `008/015/017` |

### 6.4 Ownership tạm

| Topic | Gánh gì |
|-------|---------|
| 006 | Producer semantics, operator grammar, seed-manifest compilation, parameter sweep, `generation_mode` mechanism |
| 017 | Coverage map, cell archive, local probes, surprise queue, phenotype-side consumption, budget/scan discipline |
| 015 | Lineage/provenance artifacts, invalidation semantics, contradiction storage schema |
| 013 | Common comparison-domain law, multiplicity/correction law, convergence-analysis thresholds |
| 008 | Identity vocabulary, equivalence categories, hybrid-equivalence semantics |
| 003 | Stage wiring, `protocol_lock`, breadth-activation blocker, required artifact contract |

---

## 7. Agenda vòng sau

Không có round 8 cho topic này.

Bước kế tiếp là synthesis phase:
1. Viết tài liệu self-contained theo format `final-resolution.md`, dùng proposals + round 1–7 artifacts làm evidence, không debate lại.
2. Mang toàn bộ `DEFER` residual sang đúng owner topic: `015`, `017`, `013`, `008`, `006`, `003`.
3. Chỉ quay lại `search-space-expansion` nếu có `REOPEN-*` với bằng chứng repo mới thực sự phủ định `CL-01..CL-21`.

**Evidence**: `debate/rules.md` §12-§14b; `docs/search-space-expansion/debate/gemini/gemini_debate_lan_6.md` §7; `docs/search-space-expansion/debate/codex/codex_debate_lan_6.md` §1; `docs/search-space-expansion/debate/claude/claude_debate_lan_6.md` §1, Status Table; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_6.md` §1, Status Table.

---

## 8. Change Log

| Vòng | Ngày | Agent | Tóm tắt thay đổi |
|------|------|-------|-------------------|
| 7 | 2026-03-26 | chatgptpro | Không mở issue mới; xác nhận blocker `§14b` của Codex đã hết sau khi round 6 của cả 4 agent đều hiện diện; thêm `CL-21` để khóa điều kiện dừng; bàn giao topic sang synthesis. |

**Status Table (required by `debate/rules.md` §11)**

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| OI-01 | Owner của pre-lock generation lane | Judgment call | CONVERGED | “Nếu downstream chưa echo object table của họ thì owner split vẫn chỉ là slogan.” | Authority-order reversal. Upstream phải route owner trước; downstream chỉ cần `REOPEN-*` nếu thật sự lộ gap mới. |
| OI-02 | Backbone intra-campaign + producer integration | Thiếu sót | CONVERGED | “Exact `generation_mode` fields chưa enumerate thì chưa thể đóng.” | Architecture law đã chốt; exact keys/tests là schema work của `006/003`. |
| OI-03 | Surprise lane không được nhầm novelty với value | Thiếu sót | CONVERGED | “Proof inventory chưa xong vì owner map và threshold table chưa freeze.” | Topic này chỉ cần topology + minimum inventory; exact thresholds/matrices là downstream parameterization. |
| OI-04 | Canonical provenance / 3-layer lineage | Thiếu sót | DEFER | “Field list chưa xong nên issue vẫn phải active ở đây.” | Sai owner surface. Semantic split đã khóa; field enumeration + invalidation thuộc `015`. |
| OI-05 | Cross-campaign contradiction memory | Judgment call | DEFER | “Row schema/retention chưa close nên memory issue vẫn phải active ở đây.” | Ceiling direction đã khóa; row schema/retention là downstream work của `015/017`. |
| OI-06 | Breadth-expansion vs identity/equivalence/correction coupling | Thiếu sót | CONVERGED | “Nếu exact correction/taxonomy/invalidation defaults chưa freeze thì breadth issue vẫn OPEN.” | Topic này chỉ khóa field obligation + anti-AST-only/no-LLM direction; exact defaults đi xuống owner topics. |
| OI-07 | Domain-seed / cross-domain hook | Judgment call | CONVERGED | “Cross-domain cross-pollination phải là core mechanism của v1.” | Thứ cần tái lập là composition có provenance, không phải session metaphor; domain-seed chỉ còn là optional provenance hook. |
| OI-08 | Interface-level closure vs exact-law closure | Thiếu sót | CONVERGED | “Interface layer chưa đủ; exact candidate-level defaults phải đóng ngay tại đây.” | 7-field contract là đủ ở architecture layer; exact values/defaults có owner downstream rõ ràng nên phải `DEFER`, không giữ active register. |
| NEW-01 (ChatGPT Pro) | Multiplicity control residual | Thiếu sót | DEFER | “Vì coupling đã khóa thì default law cũng phải khóa ngay ở topic này.” | Coupling đã khóa; exact correction law = `013`, invalidation matrix = `015`. |
| NEW-01 (Claude) | APE v1 scope | Thiếu sót | CONVERGED | “Structural innovation cần code generation ở v1.” | V1 chỉ cần parameterization/compile-time ideation; correctness guarantee cho free-form codegen chưa có. |

**Evidence basis for status table**: `docs/search-space-expansion/debate/gemini/gemini_debate_lan_6.md`; `docs/search-space-expansion/debate/codex/codex_debate_lan_6.md`; `docs/search-space-expansion/debate/claude/claude_debate_lan_6.md`; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_6.md`; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` (`CL-11`, `OI-07`); `debate/rules.md` §11, §13, §14b.
