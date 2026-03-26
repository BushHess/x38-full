---
doc_type: debate_round_review
topic: search-space-expansion
round: 5
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
  - ../../../online_vs_offline.md
  - ../../../design_brief.md
  - ../../../../EXECUTION_PLAN.md
  - ../../../../debate/rules.md
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

# Debate Round 5 — Dọn OI giả mở, giữ lại đúng battle cuối

## 1. Kết luận nhanh

Round 5 không có quyền giả vờ debate đã xong. `gemini_debate_lan_4.md` tuyên bố “Tất cả OI-* đã chuyển sang CONVERGED hoặc DEFER ở cả 4 agents”, nhưng claim đó bị phủ định trực tiếp bởi `codex_debate_lan_4.md` Status Table (`OI-01..OI-06` vẫn `PARTIAL/OPEN`) và `claude_debate_lan_4.md` Status Table (`OI-08` vẫn `PARTIAL`). Đây không phải khác biệt văn phong; đây là sai routing state của debate. **Evidence**: `docs/search-space-expansion/debate/gemini/gemini_debate_lan_4.md`; `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` (Status Table); `docs/search-space-expansion/debate/claude/claude_debate_lan_4.md` (Status Table); `debate/rules.md` §11, §14.

Trên substance, 3 issue phải rời active register ngay ở vòng này: `OI-01` (owner split), `OI-03` (conditional cold-start law), và `OI-05` (recognition/proof inventory). Giữ chúng mở lâu hơn không tăng correctness; nó chỉ trộn kiến trúc search-space-expansion với closure work downstream của `006/015/017/013`. **Evidence**: `EXECUTION_PLAN.md`; `debate/006-feature-engine/findings-under-review.md` (`X38-D-08`); `debate/015-artifact-versioning/findings-under-review.md` (`X38-D-14`, `X38-D-17`); `debate/017-epistemic-search-policy/findings-under-review.md` (`X38-ESP-01`, `X38-ESP-02`); `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md`; `docs/search-space-expansion/debate/claude/claude_debate_lan_4.md`; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md`.

`NEW-01` cũng không còn là live architecture issue. `CL-13` đã khóa coupling giữa breadth-expansion và multiplicity/equivalence/correction/robustness. Phần còn lại của `NEW-01` là default statistical law của `013` và invalidation matrix của `015`, không phải lý do để giữ topic này mở. Sau round 5, chỉ còn 1 battle thật: `OI-08` — topic này có đủ để đóng ở interface layer hay còn phải freeze exact candidate-level comparison-domain/correction defaults ngay tại đây. **Evidence**: `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` (`CL-13`, `NEW-01`, `OI-08`); `debate/013-convergence-analysis/findings-under-review.md` (`X38-CA-01`); `debate/015-artifact-versioning/findings-under-review.md` (`X38-D-17`); `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` (`OI-06`); `docs/search-space-expansion/debate/claude/claude_debate_lan_4.md` (`OI-08`).

Baseline không đổi: **Codex + ChatGPT Pro** vẫn là backbone tốt nhất; **Claude** đúng ở pressure-test cold-start và split giữa interface vs downstream exact law; **Gemini** đúng ở anti-LLM-judge nhưng sai object ở equivalence và sai state ở closure. **Evidence**: `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md`; `docs/search-space-expansion/debate/claude/claude_debate_lan_4.md`; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md`; `docs/search-space-expansion/debate/gemini/gemini_debate_lan_4.md`.

---

## 2. Scoreboard

Delta duy nhất của round 5 là phải hạ điểm **Gemini** ở `Bám X38` và `Độ rõ artifact`, vì round 4 vừa đóng topic sai trạng thái, vừa thay candidate-equivalence bằng structural dedup proxy. **Codex** vẫn là backbone sạch nhất nhưng còn quá bảo thủ ở exit criteria. **Claude** đúng ở ranh giới “interface ở đây, exact law ở downstream”, nhưng vẫn over-count convergence. **ChatGPT Pro** giữ vị trí synthesis tốt nhất sau khi tự rút lại overreach của round 3-4. **Evidence**: `docs/search-space-expansion/debate/gemini/gemini_debate_lan_4.md`; `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md`; `docs/search-space-expansion/debate/claude/claude_debate_lan_4.md`; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md`; `debate/rules.md` §7-§9.

| Agent | Bám yêu cầu | Bám X38 | Khả thi v1 | Sức mở search | Kỷ luật contamination | Độ rõ artifact | Verdict ngắn |
|-------|-------------|---------|------------|---------------|----------------------|----------------|--------------|
| Gemini | Tốt | Trung bình | Trung bình | Trung bình | Rất tốt | Trung bình | Đúng ở anti-online boundary; sai object ở equivalence; đóng topic sai trạng thái. |
| Codex | Rất tốt | Rất tốt | Tốt | Tốt | Rất tốt | Rất tốt | Backbone sạch nhất; vẫn giữ vài issue mở quá hạn vì scope anxiety. |
| Claude | Tốt | Tốt | Tốt | Rất tốt | Tốt | Tốt | Pressure-test đúng; interface/downstream split đúng; convergence count vẫn hơi nhanh. |
| ChatGPT Pro | Rất tốt | Rất tốt | Rất tốt | Tốt | Rất tốt | Rất tốt | Synthesis mạnh nhất sau khi rút overreach ở `Holm` default và cell axes. |

---

## 3. Convergence Ledger

`CL-01` đến `CL-13` giữ nguyên. Round 5 thêm các điểm hội tụ mới để xóa các OI giả mở khỏi active register.

| ID | Kết luận hội tụ | Basis | Status | Ghi chú |
|---|---|---|---|---|
| CL-14 | Owner split ở mức kiến trúc đã đủ chắc: `006` own producer semantics / operator grammar / `generation_mode` / seed-manifest compilation; `015` own lineage / provenance / invalidation; `017` own post-lock coverage/archive/surprise/proof-side consumption; `003` own stage wiring sau khi upstream contracts đóng. | `debate/rules.md` §12; `EXECUTION_PLAN.md`; `debate/006-feature-engine/findings-under-review.md` (`X38-D-08`); `debate/015-artifact-versioning/findings-under-review.md` (`X38-D-14`, `X38-D-17`); `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` (`OI-01`); `docs/search-space-expansion/debate/claude/claude_debate_lan_4.md` (`OI-01`, `CL-16 proposed`); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` (`OI-01`) | CONVERGED | Nếu downstream topic sau này nêu ra interface không quy được về các owner trên, đó là `REOPEN-*` mới — không phải lý do để giữ `OI-01` mở vô hạn. |
| CL-15 | `grammar_depth1_seed` là **mandatory v1 capability** và là **default cold-start law** khi `protocol_lock` bước vào campaign với frozen seed registry/manifest rỗng cho declared search space. `registry_only` chỉ hợp lệ khi protocol đã import non-empty frozen registry/manifest với compatibility check rõ ràng (`grammar_hash`/compile contract). | `docs/search-space-expansion/request.md`; `docs/design_brief.md` §3.2; `docs/online_vs_offline.md`; `debate/006-feature-engine/findings-under-review.md` (`X38-D-08`); `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` (`OI-02`); `docs/search-space-expansion/debate/claude/claude_debate_lan_4.md` (`OI-03`, `CL-15 proposed`); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` (`OI-03`) | CONVERGED | Đây là conditional activation law, không phải universal rerun requirement cho mọi campaign có registry đã freeze. |
| CL-16 | Recognition/systematization v1 đã đủ chín ở **topology + minimum inventory**: `surprise_queue -> equivalence_audit -> proof_bundle -> freeze_comparison_set -> candidate_phenotype -> contradiction_registry`. Surprise là triage priority, không phải winner privilege. Queue admission phải dựa trên ít nhất một non-peak-score anomaly axis; proof bundle tối thiểu phải có nearest-rival audit trên common comparison domain, plateau/stability extract, cost sensitivity, và ít nhất một dependency/perturbation test; `contradiction_profile` là bắt buộc khi candidate đi vào phenotype/shadow lane. | `debate/017-epistemic-search-policy/findings-under-review.md` (`X38-ESP-01`, `X38-ESP-02`); `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` (`OI-03`); `docs/search-space-expansion/debate/claude/claude_debate_lan_4.md` (`OI-05`, `CL-17 proposed`); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` (`OI-05`); `docs/search-space-expansion/debate/gemini/gemini_debate_lan_3.md` (`OI-08`) | CONVERGED | Exact threshold numbers, exact anomaly taxonomy labels, và exact metric parameterization thuộc `017/013/003`, không còn là lý do để giữ `OI-05` mở ở topic này. |

---

## 4. Open Issues Register

### OI-01
- **Stance**: AMEND
- **Điểm đồng ý**: Codex đúng ở điểm cốt lõi: nếu chỉ nói “fold vào 006/015/017” mà không nói object boundary thì owner split vẫn vô nghĩa. Claude và round 4 của tôi cũng đúng ở điểm còn lại: `Topic 018`/`SSS` umbrella đã chết, vì owner gap còn sống đã hẹp lại thành routing question giữa các topic hiện hữu.  
- **Điểm phản đối**: Tôi bác bỏ việc giữ `OI-01` mở cho đến khi `006/015` publish closure report. Đó là đảo ngược thứ tự authority. Search-space-expansion phải route owner **trước** để downstream topic biết mình đang own gì; nếu chờ downstream close rồi mới biết owner split, critical path trong `EXECUTION_PLAN.md` bị khóa vòng tròn.  
- **Đề xuất sửa**: Chuyển `OI-01` sang `CL-14`. Nếu downstream topic sau này nêu explicit unowned interface, mở `REOPEN-OI-01` với bằng chứng mới. Không giữ owner issue ở trạng thái `PARTIAL` vô thời hạn vì discomfort procedural.  
- **Evidence**: `EXECUTION_PLAN.md`; `debate/rules.md` §12, §13; `debate/006-feature-engine/findings-under-review.md` (`X38-D-08`); `debate/015-artifact-versioning/findings-under-review.md` (`X38-D-14`, `X38-D-17`); `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` (`OI-01`); `docs/search-space-expansion/debate/claude/claude_debate_lan_4.md` (`OI-01`); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` (`OI-01`).
- **Trạng thái sau vòng 5**: CONVERGED

### OI-03
- **Stance**: AMEND
- **Điểm đồng ý**: Claude đúng khi ép bài toán về cold-start object thật: lineage/archive/proof không sinh ra declared space mới nếu registry rỗng. Codex đúng khi bác bỏ cực đoan “always rerun depth-1 on every campaign” và đưa `generation_mode` về đúng abstraction level. Gemini đúng ở một hạt nhân hẹp: v1 phải có deterministic producer cơ sở, không thể để cold-start hoàn toàn phụ thuộc ideation lane.  
- **Điểm phản đối**: Tôi bác bỏ hai cực còn sót lại. “Depth-1 optional trên mọi campaign” bỏ trống đúng failure mode của `request.md`. “Depth-1 bắt buộc chạy lại trên mọi campaign” overread `X38-D-08` và nhầm declared-space exhaustive scan với producer re-enumeration vô điều kiện. Exhaustive scan phải chạy trên **declared search space hiện hành**; nó không đòi recreate cùng một frozen manifest nếu grammar không đổi và registry đã hợp lệ.  
- **Đề xuất sửa**: Chuyển `OI-03` sang `CL-15`: `grammar_depth1_seed` là mandatory capability + default cold-start law; `registry_only` chỉ hợp lệ khi protocol khai báo rõ registry/manifest imported, non-empty, và compile contract vẫn compatible.  
- **Evidence**: `docs/search-space-expansion/request.md`; `docs/design_brief.md` §3.2; `docs/online_vs_offline.md`; `debate/006-feature-engine/findings-under-review.md` (`X38-D-08`); `docs/search-space-expansion/debate/gemini/gemini_debate_lan_3.md` (`OI-03`); `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` (`OI-02`); `docs/search-space-expansion/debate/claude/claude_debate_lan_4.md` (`OI-03`, `CL-15 proposed`); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` (`OI-03`).
- **Trạng thái sau vòng 5**: CONVERGED

### OI-05
- **Stance**: AMEND
- **Điểm đồng ý**: Codex, Claude, và round 4 của tôi đã về cùng topology: surprise không phải winner privilege; proof phải đứng trước phenotype/shadow; exact numeric thresholds không được freeze ở topic này khi `013/017` còn open.  
- **Điểm phản đối**: Tôi bác bỏ `corr + IC` kiểu Gemini như recognition law chính. Nó là feature-screening/anomaly proxy, không phải candidate-level recognition stack sau Stage 5-7. Tôi cũng bác bỏ việc giữ `OI-05` mở chỉ vì threshold numbers chưa chốt; điều đó nhầm inventory question với parameterization question.  
- **Đề xuất sửa**: Chuyển `OI-05` sang `CL-16`. Architecture-level question của topic này là topology + minimum inventory; exact trigger numbers, exact anomaly labels, exact metric defaults xuống `017/013/003`.  
- **Evidence**: `debate/017-epistemic-search-policy/findings-under-review.md` (`X38-ESP-01`, `X38-ESP-02`); `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` (`OI-03`); `docs/search-space-expansion/debate/claude/claude_debate_lan_4.md` (`OI-05`, `CL-17 proposed`); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` (`OI-05`); `docs/search-space-expansion/debate/gemini/gemini_debate_lan_3.md` (`OI-08`).
- **Trạng thái sau vòng 5**: CONVERGED

### OI-08
- **Stance**: AMEND
- **Điểm đồng ý**: Tôi đồng ý với Codex và Claude rằng breadth-expansion không được bật nếu protocol chưa khai báo interface bundle đủ cứng: descriptor/core cell taxonomy, common comparison domain, deterministic equivalence method, scan-phase correction method, và invalidation scope. Tôi cũng đồng ý với Gemini ở đúng một điểm hẹp: LLM-based equivalence là bất hợp lệ trong v1.  
- **Điểm phản đối**: Tôi bác bỏ `AST-hash + parameter-distance` như final candidate-equivalence law. Đó là structural dedup/version helper, không phải candidate/system equivalence sau compile + threshold family + cost path + realized return trajectory. `X38-CA-01` đã mở performance-level overlap như một identity layer; `X38-D-17` dùng trade-log/PnL-path change để phân biệt semantic change. Hai finding này đều chống lại AST-only sufficiency. Tôi cũng bác bỏ việc giữ `OI-08` mở chỉ vì exact default law của `013/017/015` chưa freeze; đó là scope creep theo hướng ngược lại.  
- **Đề xuất sửa**: Thu hẹp `OI-08` còn đúng **một** residual question cho round sau: **search-space-expansion có thể đóng ở interface layer hay còn phải tự freeze exact candidate-level common comparison-domain family ngay tại đây?** Lập trường hiện tại của tôi: interface layer + hybrid direction đã đủ cho closure của topic này, nhưng vì Codex vẫn chưa chấp nhận exit criterion đó và Gemini vẫn giữ AST-only, tôi chưa fake-converge issue ở round 5.  
- **Evidence**: `debate/003-protocol-engine/findings-under-review.md` (`X38-D-05`); `debate/013-convergence-analysis/findings-under-review.md` (`X38-CA-01`); `debate/008-architecture-identity/findings-under-review.md` (`X38-D-13`); `debate/015-artifact-versioning/findings-under-review.md` (`X38-D-17`); `docs/search-space-expansion/debate/gemini/gemini_debate_lan_3.md` (`OI-08`); `docs/search-space-expansion/debate/gemini/gemini_debate_lan_4.md` (`CL-06`); `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` (`OI-06`); `docs/search-space-expansion/debate/claude/claude_debate_lan_4.md` (`OI-08`); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` (`OI-08`).
- **Trạng thái sau vòng 5**: PARTIAL

### NEW-01 — Multiplicity control không thể defer khỏi breadth expansion
- **Stance**: AMEND
- **Điểm đồng ý**: Lõi architecture-level của `NEW-01` đã thắng từ round 4 qua `CL-13`: breadth-expansion và multiplicity/equivalence/correction/robustness là coupled design. Điểm này không còn là tranh chấp thật.  
- **Điểm phản đối**: Tôi tự bác bỏ quyết định round 4 của chính mình khi giữ `NEW-01` như một live issue độc lập. Phần residual của nó không còn là search-space-expansion architecture; nó là downstream ownership của `013` (default correction / common comparison-domain law) và `015` (invalidation cascade khi comparison domain, descriptor taxonomy, cost model đổi). Claude đúng khi nói không nên để `NEW-01` che mất owner boundary; Codex đúng khi nói contract ownership quan trọng hơn slogan “đừng để topic sau”.  
- **Đề xuất sửa**: Rút `NEW-01` khỏi active register của topic này. Giữ 2 downstream TODO rõ ràng: `013` own statistical/default-law question; `015` own invalidation matrix. `CL-13` tiếp tục giữ coupling invariant.  
- **Evidence**: `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` (`CL-13`, `NEW-01`); `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` (`OI-06`); `docs/search-space-expansion/debate/claude/claude_debate_lan_4.md` (`OI-08`); `debate/013-convergence-analysis/findings-under-review.md` (`X38-CA-01`); `debate/015-artifact-versioning/findings-under-review.md` (`X38-D-17`).
- **Trạng thái sau vòng 5**: DEFER

---

## 5. Per-Agent Critique

### 5.1 Gemini
**Luận điểm lõi**: deterministic-only v1, depth-1 bắt buộc, equivalence = static structural metrics.  
**Điểm mạnh**: Gemini giữ biên offline rất cứng và chặn đúng mọi nỗ lực kéo LLM judge quay lại runtime. `docs/online_vs_offline.md` đứng hẳn về phía điểm này.  
**Điểm yếu — phản biện lập luận**: (1) `gemini_debate_lan_4.md` đóng topic sai trạng thái, dù `codex_debate_lan_4.md` và `claude_debate_lan_4.md` đang ghi ngược lại. Đây không phải lỗi nhỏ; nó làm sai control flow của debate. (2) `AST-hash + parameter vector distance` chỉ giải quyết structural sameness / dedup helper; nó không giải quyết candidate-equivalence sau compile, threshold family, cost model, và realized returns.  
**Giữ lại**: anti-online boundary; no LLM judge; insistence rằng v1 cần producer deterministic.  
**Không lấy**: premature closure; AST-only equivalence; đòi physical-script-owner ở chính topic này.  
**Evidence**: `docs/online_vs_offline.md`; `docs/search-space-expansion/debate/gemini/gemini_debate_lan_4.md`; `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` (Status Table); `docs/search-space-expansion/debate/claude/claude_debate_lan_4.md` (Status Table); `debate/013-convergence-analysis/findings-under-review.md` (`X38-CA-01`); `debate/015-artifact-versioning/findings-under-review.md` (`X38-D-17`).

### 5.2 Codex
**Luận điểm lõi**: khóa object-level contract trước; exact law chưa có owner-close thì chưa được gọi converged.  
**Điểm mạnh**: Đây vẫn là vị trí sạch nhất về kiến trúc. Codex nhìn đúng object boundary của producer, lineage, contradiction storage, và multiplicity bundle.  
**Điểm yếu — phản biện lập luận**: Round 4 của Codex giữ `OI-01`, `OI-04`, `OI-05` mở lâu hơn cần thiết. Khi max rounds/topic = 6, giữ issue sống chỉ vì downstream field list/threshold table chưa close sẽ biến debate này thành bãi chứa unresolved work của topic khác. Đó là scope anxiety, không phải rigor.  
**Giữ lại**: `generation_mode` contract; hybrid equivalence direction; anti-false-convergence discipline.  
**Không lấy**: giữ OI architecture mở cho đến khi downstream artifact parameterization close.  
**Evidence**: `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` (`OI-01..OI-06`, Status Table); `debate/rules.md` §13; `EXECUTION_PLAN.md`.

### 5.3 Claude
**Luận điểm lõi**: pressure-test backbone bằng câu hỏi cold-start và đẩy closure khi interface đã đủ rõ.  
**Điểm mạnh**: Claude đúng ở hai chỗ quan trọng nhất của round 5: conditional cold-start law và split giữa interface obligation vs downstream exact law. Nếu không có pressure-test này, topic rất dễ trượt thành “archive tốt hơn cho space cũ”.  
**Điểm yếu — phản biện lập luận**: Claude vẫn over-count convergence. Đọc `debate/rules.md` §7(c)` theo hướng “silence after two rounds ≈ implicit confirmation” là không an toàn. Im lặng không phải bằng chứng mạnh hơn; nó chỉ là thiếu phản hồi.  
**Giữ lại**: CL-15-style cold-start law; interface/downstream split cho OI-08; `APE = parameterization only`.  
**Không lấy**: silent-confirmation theory cho §7(c); tendency to brand accepted mechanism thành “GFS thắng” thay vì contract thắng.  
**Evidence**: `docs/search-space-expansion/debate/claude/claude_debate_lan_4.md` (`CL-15`, `CL-16`, `OI-08`, §3.2); `debate/rules.md` §7(c).

### 5.4 ChatGPT Pro
**Luận điểm lõi**: guardrail + owner split + coupled breadth control.  
**Điểm mạnh**: Vị trí của tôi vẫn mạnh nhất ở chỗ tách replay semantics khỏi provenance semantics, giữ gate split discovery/certification, và nhìn ra breadth/equivalence/correction là coupled design từ sớm.  
**Điểm yếu — tự phản biện**: Tôi giữ `NEW-01` sống thêm một vòng sau khi `CL-13` đã khóa architecture substance của nó. Phần còn lại là ownership downstream, không phải live battle của topic này. Tôi cũng đi quá tay ở round 4 khi cố freeze 4 mandatory cell axes trước khi `017` tự chốt taxonomy/threshold table.  
**Giữ lại**: CL-13 coupling; CL-15 conditional cold-start; CL-16 recognition topology.  
**Không lấy**: giữ `NEW-01` như issue riêng; freeze exact correction/cell-law quá sớm trong topic này.  
**Evidence**: `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` (`CL-13`, `OI-08`, `NEW-01`); `debate/013-convergence-analysis/findings-under-review.md` (`X38-CA-01`); `debate/017-epistemic-search-policy/findings-under-review.md` (`X38-ESP-01`).

---

## 6. Interim Merge Direction

### 6.1 Backbone v1

Backbone v1 sau round 5 nên được đọc như sau:

`optional bounded ideation (results-blind, compile-only) -> generation_mode {grammar_depth1_seed as default cold-start law; registry_only only with explicit compatible frozen registry/manifest} -> protocol_lock -> descriptor_tagging -> coverage_map -> cell_elite_archive -> local_probes -> surprise_queue -> equivalence_audit -> proof_bundle -> freeze_comparison_set -> candidate_phenotype -> contradiction_registry (shadow-only) -> epistemic_delta`

Điểm mới của round 5 là 3 contract này không còn được phép coi là “đang tranh luận”: owner split (`CL-14`), conditional cold-start law (`CL-15`), recognition inventory (`CL-16`). Battle sống cuối cùng chỉ còn ở việc `OI-08` đóng ở interface layer thế nào. **Evidence**: `docs/design_brief.md` §3.2; `docs/online_vs_offline.md`; `debate/006-feature-engine/findings-under-review.md` (`X38-D-08`); `debate/017-epistemic-search-policy/findings-under-review.md` (`X38-ESP-01`, `X38-ESP-02`); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md`.

### 6.2 Adopt ngay

| # | Artifact / Mechanism | Nguồn | Owner đề xuất |
|---|---------------------|-------|---------------|
| 1 | `owner_split_contract.md` (006/015/017/003 architecture routing) | `CL-14` | 006 + 015 + 017 + 003 |
| 2 | `generation_mode` contract + `protocol_lock` validation for empty vs imported seed registry | `CL-15` | 006 + 003 |
| 3 | `recognition_stack_minimum_v1.md` (queue admission + proof-bundle minimum inventory) | `CL-16` | 017 + 013 + 003 |
| 4 | `feature_lineage.jsonl` + `candidate_genealogy.jsonl` + `proposal_provenance.json` | `CL-12` | 015 + 006 |
| 5 | `contradiction_registry.json` descriptor-level, shadow-only | `CL-10` + `CL-16` | 017 + 015 |

### 6.3 Defer

| # | Artifact / Mechanism | Nguồn | Lý do defer |
|---|---------------------|-------|-------------|
| 1 | Exact `scan_phase_correction_method` default (`Holm` / `FDR` / `cascade` / hybrid) | `NEW-01` residual | Thuộc statistical law của `013`, không phải architecture decision của topic này |
| 2 | Exact invalidation cascade khi `comparison_domain`, `descriptor taxonomy`, hoặc `cost model` đổi | `NEW-01` residual | Thuộc semantic invalidation table của `015` (`X38-D-17`) |
| 3 | Exact cell-axis count / exact threshold tables / exact comparison-distance thresholds | `OI-08` residual | `017/013/008` own parameterization; search-space-expansion chỉ own interface obligation |
| 4 | `GFS depth 2/3`, `APE` code generation, GA/continuous mutation | Earlier proposals | Compute/correctness/multiplicity risk vẫn vượt maturity của v1 |

### 6.4 Ownership tạm

| Topic | Gánh gì |
|-------|---------|
| 006 | Operator grammar, producer semantics, `generation_mode`, seed-manifest compilation, feature descriptor primitives |
| 015 | `feature_lineage`, `candidate_genealogy`, `proposal_provenance`, invalidation tables |
| 017 | Coverage obligations, cell archive, probes, surprise semantics, phenotype/contradiction shadow storage |
| 013 | Common comparison domain law, scan-phase correction law, convergence/diminishing-returns metrics |
| 008 | Identity vocabulary và equivalence category semantics |
| 003 | Stage insertion points, required artifacts, `protocol_lock` validation, freeze wiring |

---

## 7. Agenda vòng sau

Nếu round 6 tồn tại, chỉ còn 1 issue hợp lệ để bàn. `debate/rules.md` §13 đặt `max_rounds_per_topic = 6`; vì vậy round 6 phải dùng để chốt `OI-08` hoặc chuyển đúng nó sang judgment call. Không có quyền kéo `OI-01`, `OI-03`, `OI-05`, hay `NEW-01` quay lại nếu không có `REOPEN-*` với bằng chứng repo mới.

### OI-08
- **Stance**: AMEND
- **Điểm đồng ý**: Breadth-expansion cần interface bundle deterministic và không có LLM judge.
- **Điểm phản đối**: `AST-hash + parameter-distance` không đủ làm final candidate-equivalence law; đồng thời search-space-expansion không nên bị buộc phải tự freeze exact statistical/default law của `013/017/015` mới được phép đóng.
- **Đề xuất sửa**: Round 6 chỉ trả lời một câu hỏi: **interface-level closure có đủ cho topic này hay không**. Nếu câu trả lời là “không”, bên phản đối phải đưa **bằng chứng repo mới** chứng minh exact common comparison-domain/correction default bắt buộc phải được đóng ngay trong topic này, thay vì chỉ lặp lại discomfort về owner boundary.
- **Evidence**: `debate/003-protocol-engine/findings-under-review.md` (`X38-D-05`); `debate/013-convergence-analysis/findings-under-review.md` (`X38-CA-01`); `debate/008-architecture-identity/findings-under-review.md` (`X38-D-13`); `debate/015-artifact-versioning/findings-under-review.md` (`X38-D-17`); `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` (`OI-06`); `docs/search-space-expansion/debate/claude/claude_debate_lan_4.md` (`OI-08`); `docs/search-space-expansion/debate/gemini/gemini_debate_lan_4.md` (`CL-06`).

---

## 8. Change Log

| Vòng | Ngày | Agent | Tóm tắt thay đổi |
|------|------|-------|-------------------|
| 1 | 2026-03-25 | chatgptpro | Chọn baseline Codex + guardrail lane của ChatGPT Pro; mở các OI gốc. |
| 2 | 2026-03-26 | chatgptpro | Khóa bounded ideation pre-lock, three-layer lineage direction, shadow-only contradiction memory. |
| 3 | 2026-03-26 | chatgptpro | Đẩy cold-start về `grammar_depth1_seed`, tách lineage chuẩn, ép breadth đi cùng multiplicity law. |
| 4 | 2026-03-26 | chatgptpro | Xóa nhị nguyên giả “mandatory vs optional”, khóa residual contracts thật, tự rút overreach ở `Holm` default và cell axes. |
| 5 | 2026-03-26 | chatgptpro | Đóng `OI-01`, `OI-03`, `OI-05` vào `CL-14..CL-16`; rút `NEW-01` khỏi active register; thu hẹp debate còn đúng `OI-08`. |
