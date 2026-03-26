---
doc_type: debate_round_review
topic: search-space-expansion
round: 4
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

# Debate Round 4 — Xóa nhị nguyên giả “mandatory vs optional”, khóa residual contracts thật

## 1. Kết luận nhanh

Round 4 không còn chỗ cho việc giả vờ landscape vẫn rộng. Sau round 3, `SSS`/online runtime đã chết về mặt kiến trúc; domain-seed như core engine cũng đã chết; split lineage/provenance 3 lớp về thực chất đã rõ. Cái còn sống chỉ là producer contract, cold-start law, proof inventory, và bundle ràng buộc breadth với identity/equivalence/correction.

Tôi chuyển `OI-07` sang `CONVERGED`, chuyển phần semantic split của `OI-04` sang `CONVERGED` và đẩy residual field/invalidation matrix của nó xuống `DEFER` cho Topic `015`. Tôi giữ `OI-01`, `OI-03`, `OI-05`, `OI-08`, và `NEW-01` là các blocker thật. Tôi cũng sửa chính mình: round 3 của tôi đi quá xa khi cố khóa luôn `Holm` làm default; evidence hiện có chỉ đủ mạnh để khóa việc **phải khai báo** `comparison_domain + equivalence_method + scan_phase_correction_method + minimum_robustness_bundle` trước khi breadth mechanism được bật, chưa đủ mạnh để khóa công thức mặc định ngay tại topic này.

Điều kiện dừng của topic chưa đạt. Sau round 4, debate chỉ còn giá trị nếu các agent phản hồi vào 5 residual blockers nêu trên; mọi nỗ lực kéo lại `SSS`, `Topic 018`, prompt ancestry canonical, hoặc LLM-based equivalence là tranh luận lạc đề và đi ngược `docs/online_vs_offline.md` cùng `debate/rules.md` §12.

**Evidence**: `docs/online_vs_offline.md`; `docs/design_brief.md`; `debate/rules.md` §12; `docs/search-space-expansion/debate/gemini/gemini_debate_lan_3.md` (OI-03, OI-08); `docs/search-space-expansion/debate/codex/codex_debate_lan_3.md` (OI-01..OI-06); `docs/search-space-expansion/debate/claude/claude_debate_lan_3.md` (CL-11..CL-14 proposed, OI-01, OI-03, OI-05, OI-08); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_3.md` (OI-01, OI-03, OI-04, OI-05, OI-07, OI-08, NEW-01).

---

## 2. Scoreboard

Delta duy nhất ở round 4 là: **Codex** được cộng điểm vì round 3 đã explicit hơn về `deterministic depth-1 compiled enumeration`; **Claude** giữ vai trò pressure-test đúng chỗ; **Gemini** vẫn đúng ở anti-online nhưng tiếp tục tấn công sai object ở equivalence; **ChatGPT Pro** tự trừ điểm vì round 3 đã overfreeze `Holm` và over-commit một cell axis chưa đủ evidence.

| Agent | Bám yêu cầu | Bám X38 | Khả thi v1 | Sức mở search | Kỷ luật contamination | Độ rõ artifact | Verdict ngắn |
|-------|-------------|---------|------------|---------------|----------------------|----------------|--------------|
| Gemini | Tốt | Tốt | Trung bình | Tốt | Rất tốt | Trung bình | Anti-online đúng, nhưng `AST-hash only` cho equivalence là sai object. |
| Codex | Rất tốt | Rất tốt | Rất tốt | Tốt | Rất tốt | Rất tốt | Backbone sạch nhất; vẫn quá dè dặt ở exact default laws. |
| Claude | Tốt | Tốt | Tốt | Rất tốt | Tốt | Tốt | Pressure-test cold-start đúng; còn xu hướng rename cơ chế đã được chấp nhận thành “GFS thắng”. |
| ChatGPT Pro | Rất tốt | Rất tốt | Rất tốt | Tốt | Rất tốt | Tốt | Guardrail + synthesis mạnh; round 4 sửa overreach ở `Holm` default và cell axes. |

**Evidence**: `docs/search-space-expansion/debate/gemini/gemini_debate_lan_3.md`; `docs/search-space-expansion/debate/codex/codex_debate_lan_3.md`; `docs/search-space-expansion/debate/claude/claude_debate_lan_3.md`; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_3.md`; `docs/online_vs_offline.md`; `docs/design_brief.md`.

---

## 3. Convergence Ledger

Giữ `CL-01` đến `CL-10` từ round 3. Round 4 chỉ thêm các điểm mà landscape round 3 đã đủ hẹp để khóa ở mức kiến trúc.

| ID | Kết luận hội tụ | Basis | Status | Ghi chú |
|---|---|---|---|---|
| CL-11 | `domain_hint_ref` / cross-domain seed chỉ là supplementary provenance hook; không có replay semantics, invalidation semantics, budget semantics, hay control-law semantics trong v1. | `docs/search-space-expansion/debate/gemini/gemini_propone.md`; `docs/search-space-expansion/debate/gemini/gemini_debate_lan_3.md` (CL-04, anti-online framing); `docs/search-space-expansion/debate/codex/codex_debate_lan_3.md` (OI-04); `docs/search-space-expansion/debate/claude/claude_debate_lan_3.md` (CL-12 proposed); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_3.md` (OI-07); `docs/online_vs_offline.md` | CONVERGED | Nếu tương lai có domain catalog, nó sống ở authoring provenance layer, không ở replay path. |
| CL-12 | Canonical provenance phải tách 3 lớp: `feature_lineage`, `candidate_genealogy`, `proposal_provenance`; chỉ 2 lớp đầu nằm trên replay path. | `docs/search-space-expansion/debate/gemini/gemini_debate_lan_3.md` (CL-04); `docs/search-space-expansion/debate/codex/codex_debate_lan_3.md` (OI-04); `docs/search-space-expansion/debate/claude/claude_debate_lan_3.md` (CL-13 proposed); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_3.md` (OI-04); `debate/015-artifact-versioning/findings-under-review.md` (`X38-D-14`, `X38-D-17`) | CONVERGED | Exact field list và invalidation matrix còn lại được hạ xuống residual của `OI-04` và giao cho Topic `015`. |
| CL-13 | Breadth-expansion không được bật nếu protocol chưa khai báo `comparison_domain`, `equivalence_method`, `scan_phase_correction_method`, và `minimum_robustness_bundle`. | `docs/design_brief.md` §3.2; `debate/003-protocol-engine/findings-under-review.md` (`X38-D-05`); `debate/013-convergence-analysis/findings-under-review.md` (`X38-CA-01`); `docs/search-space-expansion/debate/codex/codex_debate_lan_3.md` (OI-06); `docs/search-space-expansion/debate/claude/claude_debate_lan_3.md` (OI-08, NEW-01 merge note); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_3.md` (NEW-01) | CONVERGED | Exact default formula và invalidation cascade vẫn mở ở `NEW-01`. |

---

## 4. Open Issues Register

Chỉ cập nhật delta cho các issue còn sống từ round 3 của tôi, hoặc các issue round 3 của agent khác cho thấy residual vẫn tồn tại thực chất.

### OI-01
- **Stance**: AMEND
- **Điểm đồng ý**: Tất cả các round 3 thực chất đã khóa cùng một split ở mức kiến trúc: `006` own producer semantics / operator grammar / compilation; `015` own provenance + lineage + invalidation; `017` own coverage/archive/proof-side consumption; `003` own stage wiring sau khi upstream contracts đóng. Không còn agent nào bảo vệ việc mở lại `Topic 018` umbrella hay dựng `SSS` thành subsystem. Điều này đủ mạnh để xem owner split đã hẹp tới mức chỉ còn residual procedural wording.  
- **Điểm phản đối**: Tôi bác bỏ cách Gemini đòi “physical script owner” ngay trong issue này. Đó là nhầm abstraction level. Topic search-space-expansion phải khóa **contract ownership**, không phải tên file `.py` hay CLI entrypoint. Tôi cũng bác bỏ việc giữ issue mở chỉ vì chưa có template closure-report cụ thể; `debate/rules.md` §12 đã nói đủ rõ rằng topic mới chỉ mở khi có unresolved cross-topic contract thật, không phải vì khó chịu ở mức triển khai.  
- **Đề xuất sửa**: Khóa architecture-level split như trên, nhưng giữ issue ở `PARTIAL` thêm 1 vòng duy nhất để chờ wording thống nhất cho closure trigger: chỉ khi `006` hoặc `015` closure report nêu rõ một interface không thể quy về `006/015/017/003/013/008` thì mới được mở topic hẹp mới. Nếu không có wording tốt hơn ở round 5, issue này phải rời active register.  
- **Evidence**: `debate/rules.md` §12; `EXECUTION_PLAN.md`; `debate/006-feature-engine/findings-under-review.md` (`X38-D-08`); `debate/015-artifact-versioning/findings-under-review.md` (`X38-D-14`, `X38-D-17`); `docs/search-space-expansion/debate/codex/codex_debate_lan_3.md` (OI-01); `docs/search-space-expansion/debate/claude/claude_debate_lan_3.md` (OI-01); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_3.md` (OI-01); `docs/search-space-expansion/debate/gemini/gemini_debate_lan_3.md` (critique against “abstract ownership”).
- **Trạng thái sau vòng 4**: PARTIAL

### OI-03
- **Stance**: AMEND
- **Điểm đồng ý**: Claude và Gemini đúng khi nói rằng lineage/archive/proof không tự giải quyết bài toán **empty-registry cold-start**. Codex cũng đúng khi nhắc `X38-D-08` đã giả định registry/families có thể tồn tại; không phải mọi campaign đều bắt đầu từ số 0. Lập trường đúng của round 4 vì vậy không còn là “mandatory vs optional” theo kiểu tuyệt đối.  
- **Điểm phản đối**: Tôi bác bỏ cả hai cực đoan. “Always-run depth-1 for every campaign” là lãng phí và bỏ qua trường hợp protocol đã nhập một seed manifest đóng băng. “Depth-1 optional trên mọi campaign” thì bỏ trống đúng failure mode mà `docs/search-space-expansion/request.md` đang nhắm: không có quy trình chủ động tạo đối tượng để scanner quét khi search space ban đầu trống.  
- **Đề xuất sửa**: Khóa **conditional cold-start law** cho v1: nếu `protocol lock` bước vào campaign với registry/seed manifest rỗng cho search space đó (new asset, new universe, hoặc chưa import frozen seed set), thì `grammar_depth1_seed` là **mandatory default**. Nếu protocol đã import non-empty frozen registry/seed manifest, depth-1 enumeration có thể bị bỏ qua nhưng chỉ bằng declaration rõ ràng trong protocol, không bằng “ngầm hiểu là optional”. `bounded ideation` vẫn chỉ là lane phụ trợ pre-lock; nó không thay thế được missing cold-start coverage. `depth-2+`, `APE` code generation, GA/continuous mutation tiếp tục `DEFER`.  
- **Evidence**: `docs/search-space-expansion/request.md`; `docs/design_brief.md` §3.2 (Stage 3 exhaustive scan); `docs/online_vs_offline.md`; `debate/006-feature-engine/findings-under-review.md` (`X38-D-08`); `docs/search-space-expansion/debate/gemini/gemini_debate_lan_3.md` (OI-03); `docs/search-space-expansion/debate/codex/codex_debate_lan_3.md` (OI-01, OI-02); `docs/search-space-expansion/debate/claude/claude_debate_lan_3.md` (OI-03); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_3.md` (OI-03).
- **Trạng thái sau vòng 4**: PARTIAL

### OI-04
- **Stance**: AMEND
- **Điểm đồng ý**: Split semantics của provenance/lineage không còn là tranh chấp thực chất nữa. Codex, Claude, và tôi đều đã về cùng một hình: `feature_lineage` + `candidate_genealogy` + `proposal_provenance`; Gemini cũng không còn giữ prompt ancestry như canonical replay path.  
- **Điểm phản đối**: Giữ `OI-04` ở active register như thể câu hỏi kiến trúc còn mở là sai. Câu hỏi còn lại bây giờ không phải “có tách 3 lớp không”, mà là `015` sẽ enumerate field list và invalidation matrix cụ thể ra sao. Đó là downstream work của Topic `015`, không còn là tranh luận search-space-expansion ở mức backbone.  
- **Đề xuất sửa**: Chuyển semantic split sang `CL-12`. Hạ residual của `OI-04` xuống `DEFER`, với checklist hẹp cho Topic `015`: (1) `feature_lineage` phải own mọi field làm thay đổi compile semantics của feature; (2) `candidate_genealogy` phải own mọi field làm thay đổi role assignment / architecture composition / threshold family; (3) `proposal_provenance` không bao giờ invalidate replay path; nó chỉ đổi audit trail.  
- **Evidence**: `debate/015-artifact-versioning/findings-under-review.md` (`X38-D-14`, `X38-D-17`); `docs/search-space-expansion/debate/gemini/gemini_debate_lan_3.md` (CL-04); `docs/search-space-expansion/debate/codex/codex_debate_lan_3.md` (OI-04); `docs/search-space-expansion/debate/claude/claude_debate_lan_3.md` (CL-13 proposed); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_3.md` (OI-04).
- **Trạng thái sau vòng 4**: DEFER

### OI-05
- **Stance**: AMEND
- **Điểm đồng ý**: Topology của recognition stack đã đủ hẹp để không bàn lại từ đầu: `surprise_queue -> equivalence_audit -> proof_bundle -> freeze_comparison_set -> candidate_phenotype -> shadow_registry`. Surprise chỉ là triage priority; human chỉ chen vào ở ambiguity / explanation / deployment; mọi candidate đi vào phenotype/shadow lane đều phải đi qua machine-verifiable proof trước.  
- **Điểm phản đối**: Tôi bác bỏ cả hai cực: Gemini-style `orthogonality + IC` như recognition law chính là quá hẹp; Claude-style numeric thresholds khóa sớm ở chính topic này cũng là quá tay so với evidence base hiện có. Codex đúng ở chỗ exact numbers chưa freeze, nhưng nếu giữ issue ở mức “cứ để downstream lo” thì topic này vẫn không khóa được inventory tối thiểu cho v1.  
- **Đề xuất sửa**: Khóa **obligation-level inventory** ngay tại đây, numeric thresholds defer cho `017/013`: `surprise_queue` chỉ nhận candidate có ít nhất một anomaly axis **không phải peak-score** từ tập `{decorrelation, plateau_width, cost_stability, cross_resolution_consistency, contradiction_resurrection}`. `proof_bundle` tối thiểu phải có: (1) nearest-rival equivalence audit trên common comparison domain; (2) plateau/stability extract; (3) cost sensitivity; (4) ít nhất một dependency stressor (`ablation` hoặc `split perturbation`); (5) `contradiction_profile` nếu candidate đi vào phenotype/shadow lane. `semantic_recovery` nếu tồn tại chỉ chạy **sau proof, sau freeze, không có authority**.  
- **Evidence**: `debate/017-epistemic-search-policy/findings-under-review.md` (`X38-ESP-01`, `X38-ESP-02`); `docs/search-space-expansion/debate/codex/codex_debate_lan_3.md` (OI-03); `docs/search-space-expansion/debate/claude/claude_debate_lan_3.md` (OI-05); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_3.md` (OI-05); `docs/search-space-expansion/debate/gemini/gemini_propone.md`.
- **Trạng thái sau vòng 4**: PARTIAL

### OI-07
- **Stance**: AGREE
- **Điểm đồng ý**: Round 3 đã đủ rõ: cross-domain / domain-seed có giá trị như ideation feedstock và provenance hook. Không cần xóa nó khỏi hệ; chỉ cần đặt nó đúng chỗ.  
- **Điểm phản đối**: Giữ `OI-07` ở trạng thái mở là artificial. Không còn agent nào ở round 3 bảo vệ domain-seed như control law, budget primitive, replay input, hay canonical grammar field. Argument mạnh nhất còn lại — “VDO đến từ cảm hứng domain khác nên domain catalog phải là core engine” — không đứng vững, vì điều được tái lập có hệ thống là **composition** chứ không phải `prompt mood` hay `domain metaphor`.  
- **Đề xuất sửa**: Chuyển issue sang `CL-11`. `domain_hint_ref` / `cross_domain_seed_ref` sống ở `proposal_provenance.json` như supplementary provenance. Hết.  
- **Evidence**: `docs/online_vs_offline.md`; `docs/search-space-expansion/debate/gemini/gemini_propone.md`; `docs/search-space-expansion/debate/codex/codex_debate_lan_3.md` (OI-04); `docs/search-space-expansion/debate/claude/claude_debate_lan_3.md` (CL-12 proposed); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_3.md` (OI-07).
- **Trạng thái sau vòng 4**: CONVERGED

### OI-08
- **Stance**: AMEND
- **Điểm đồng ý**: Codex và Claude đúng rằng v1 phải có interface bundle đủ cứng cho cell axes, comparison domain, equivalence method, và correction hook. Gemini cũng đúng ở một điểm hẹp: LLM-based equivalence là bất hợp lệ trong v1 vì vi phạm determinism.  
- **Điểm phản đối**: Gemini tấn công sai object khi đòi `AST-hash + parameter distance` như backbone equivalence. Đó là **structural identity check**, không phải candidate/system equivalence. Hai manifests khác nhau có thể cho phenotype tương đương sau compile + thresholding + cost path; ngược lại, cùng AST với cost model hoặc threshold family khác có thể không còn tương đương. Tôi cũng tự sửa round 3 của mình: 5 mandatory strategy cell axes là hơi tham; `holding_bucket` chưa đủ evidence để bắt buộc ở v1 nếu `turnover_bucket` đã có.  
- **Đề xuất sửa**: Khóa 4 mandatory strategy cell axes cho v1: `mechanism_family`, `architecture_depth`, `turnover_bucket`, `timeframe_binding`. `holding_bucket`, `cost_elasticity_bucket`, `plateau_bucket`, `regime_logic_flag`, `complexity_tier` là **annotations** cho v1, chưa là cell axes bắt buộc. Equivalence v1 là **2-layer contract**: (1) deterministic structural pre-bucket dưới `006/015`; (2) behavioral nearest-rival audit trên `paired_daily_returns_after_costs` dưới `013/008`. Không có LLM judge; cũng không có AST-only sufficiency.  
- **Evidence**: `debate/017-epistemic-search-policy/findings-under-review.md` (`X38-ESP-01`, `X38-ESP-02`); `debate/013-convergence-analysis/findings-under-review.md` (`X38-CA-01`); `debate/015-artifact-versioning/findings-under-review.md` (`X38-D-17`); `docs/search-space-expansion/debate/gemini/gemini_debate_lan_3.md` (OI-08); `docs/search-space-expansion/debate/codex/codex_debate_lan_3.md` (OI-06); `docs/search-space-expansion/debate/claude/claude_debate_lan_3.md` (OI-08); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_3.md` (OI-08).
- **Trạng thái sau vòng 4**: PARTIAL

### NEW-01 — Multiplicity control không thể defer khỏi breadth expansion
- **Stance**: AMEND
- **Điểm đồng ý**: Lõi của `NEW-01` đã thắng và được khóa vào `CL-13`: breadth-expansion là coupled design với comparison domain, equivalence method, correction method, và minimum robustness bundle. Điểm này bây giờ không còn nên tranh luận lại.  
- **Điểm phản đối**: Tôi bác bỏ chính overreach của round 3 của mình: evidence chưa đủ để tuyên bố `Holm` là default law của v1 ngay tại topic này. Nhưng tôi cũng bác bỏ đề xuất của Claude muốn nuốt trọn `NEW-01` vào `OI-08`, vì làm vậy sẽ che mất hai residual còn sống: default correction formula và invalidation cascade.  
- **Đề xuất sửa**: Thu hẹp `NEW-01` còn đúng 2 câu hỏi: (1) default `scan_phase_correction_method` của Stage 3 breadth là gì (`Holm` / `FDR` / `cascade` / hybrid); (2) invalidation cascade ra sao khi `comparison_domain`, `descriptor taxonomy`, hoặc `cost model` đổi. `paired_daily_returns_after_costs` vẫn là candidate mạnh nhất cho common comparison domain ở thời điểm này, nhưng nếu bên phản biện muốn thay, họ phải đưa **contract thay thế hoàn chỉnh**, không được chỉ nói “để topic sau”.  
- **Evidence**: `debate/003-protocol-engine/findings-under-review.md` (`X38-D-05`); `debate/013-convergence-analysis/findings-under-review.md` (`X38-CA-01`); `docs/design_brief.md` §3.2; `docs/search-space-expansion/debate/codex/codex_debate_lan_3.md` (OI-06); `docs/search-space-expansion/debate/claude/claude_debate_lan_3.md` (OI-08, NEW-01 merge note); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_3.md` (NEW-01).
- **Trạng thái sau vòng 4**: PARTIAL

---

## 5. Per-Agent Critique

### 5.1 Gemini
**Luận điểm lõi**: offline-first, mandatory depth-1, static equivalence.  
**Điểm mạnh**: Anti-online boundary của Gemini vẫn hữu ích để chặn mọi nỗ lực kéo `SSS` hoặc LLM-judge quay lại v1. `docs/online_vs_offline.md` đứng về phía Gemini ở điểm này.  
**Điểm yếu — phản biện lập luận**: `AST-hash + parameter distance` chỉ giải quyết **code/config sameness**, không giải quyết **candidate/system equivalence** trên common evaluation domain. `X38-D-17` còn nói rõ semantic invalidation là chuyện “trade log/PnL path có đổi không”, không phải chỉ “source text có giống không”. Vì vậy Gemini đúng khi chặn LLM equivalence, nhưng sai khi thay nó bằng một proxy quá hẹp.  
**Giữ lại**: deterministic anti-online boundary; insistence rằng cold-start phải có producer cụ thể.  
**Không lấy**: AST-only equivalence; universal always-run depth-1 cho mọi campaign.  
**Evidence**: `docs/online_vs_offline.md`; `debate/015-artifact-versioning/findings-under-review.md` (`X38-D-17`); `debate/013-convergence-analysis/findings-under-review.md` (`X38-CA-01`); `docs/search-space-expansion/debate/gemini/gemini_debate_lan_3.md` (OI-03, OI-08).

### 5.2 Codex
**Luận điểm lõi**: freeze interface bundle và artifact semantics trước khi tăng breadth.  
**Điểm mạnh**: Codex vẫn là baseline sạch nhất cho backbone: producer contract, lineage split, archive/proof stack, contradiction registry shadow-only. Round 3 của Codex explicit hơn nhiều về `deterministic depth-1 compiled enumeration`, đây là tiến bộ thật.  
**Điểm yếu — phản biện lập luận**: Codex vẫn có xu hướng để quá nhiều default law rơi xuống “topic downstream”. Điều đó an toàn về mặt scope, nhưng nếu giữ quá lâu thì cold-start question của `request.md` vẫn không được giải object-level. Issue `OI-03` cần ít nhất một state machine condition, không thể chỉ dừng ở “compiled manifest somewhere upstream”.  
**Giữ lại**: pre-lock authoring contract; CL-13 coupling; three-layer lineage; shadow-only contradiction memory.  
**Không lấy**: perpetual agnosticism ở cold-start/default law.  
**Evidence**: `docs/search-space-expansion/debate/codex/codex_debate_lan_3.md` (OI-01..OI-06); `debate/006-feature-engine/findings-under-review.md` (`X38-D-08`); `debate/003-protocol-engine/findings-under-review.md` (`X38-D-05`).

### 5.3 Claude
**Luận điểm lõi**: pressure-test backbone bằng câu hỏi “ai/cái gì tạo feature mới”.  
**Điểm mạnh**: Đây vẫn là đóng góp giá trị nhất của Claude cho round 3-4. Nếu không có pressure test này, backbone rất dễ trượt thành “archive tốt hơn cho declared space cũ”. Claude cũng làm đúng khi đã rút `SSS`, `Topic 018`, và `APE` codegen ra khỏi core v1.  
**Điểm yếu — phản biện lập luận**: Claude có xu hướng đếm hội tụ nhanh hơn `debate/rules.md` §7 cho phép và đôi lúc rename cơ chế đã được chấp nhận (`deterministic depth-1 grammar enumeration`) thành “GFS đã thắng”. Ở round 4, cái phải thắng là **contract đúng**, không phải thương hiệu proposal nào. Claude cũng còn xu hướng freeze exact cell/correction structure sớm hơn evidence hỗ trợ.  
**Giữ lại**: cold-start pressure test; bounded ideation lane; ép giảm số cell axes bắt buộc.  
**Không lấy**: over-counted convergence; over-specified exact laws ở topic này.  
**Evidence**: `debate/rules.md` §7; `docs/search-space-expansion/debate/claude/claude_debate_lan_3.md` (CL-11..CL-14 proposed, OI-03, OI-08); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_3.md` (OI-03, OI-08).

### 5.4 ChatGPT Pro
**Luận điểm lõi**: guardrail + synthesis + contract splitting.  
**Điểm mạnh**: Điểm mạnh vẫn giữ nguyên: tách đúng replay semantics khỏi provenance semantics, giữ gate split, và nhìn ra breadth/equivalence/correction là coupled design.  
**Điểm yếu — tự phản biện**: Round 3 của tôi đi quá xa ở 2 chỗ: (1) cố freeze `Holm` làm default correction law dù `X38-D-05` và `X38-CA-01` vẫn open; (2) đòi `holding_bucket` là mandatory axis khi evidence hiện tại chưa cho thấy nó độc lập đủ với `turnover_bucket` để đáng trả chi phí cell explosion trong v1. Round 4 sửa cả hai chỗ.  
**Giữ lại**: conditional cold-start law; three-layer provenance; hybrid equivalence; CL-13 coupling.  
**Không lấy**: premature fixation of exact correction formula; quá nhiều mandatory cell axes.  
**Evidence**: `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_3.md` (OI-03, OI-04, OI-08, NEW-01); `debate/003-protocol-engine/findings-under-review.md` (`X38-D-05`); `debate/013-convergence-analysis/findings-under-review.md` (`X38-CA-01`).

---

## 6. Interim Merge Direction

### 6.1 Backbone v1

Backbone v1 sau round 4 nên được viết lại gọn và cứng như sau:

`optional bounded ideation (results-blind, compile-only) -> conditional grammar_depth1_seed (mandatory when declared registry / seed manifest is empty) -> compile_manifest -> feature_lineage / candidate_genealogy / proposal_provenance -> descriptor_tagging -> coverage_map -> cell_elite_archive -> local_probes -> surprise_queue -> equivalence_audit -> proof_bundle -> freeze_comparison_set -> candidate_phenotype -> contradiction_registry (shadow-only) -> epistemic_delta`

Hard blocker mới phải viết thẳng vào contract: breadth mechanism **không được bật** nếu protocol chưa khai báo `comparison_domain`, `equivalence_method`, `scan_phase_correction_method`, và `minimum_robustness_bundle`.

**Evidence**: `docs/design_brief.md` §3.2; `docs/online_vs_offline.md`; `debate/017-epistemic-search-policy/findings-under-review.md` (`X38-ESP-01`, `X38-ESP-02`); `debate/006-feature-engine/findings-under-review.md` (`X38-D-08`); `docs/search-space-expansion/debate/codex/codex_debate_lan_3.md`; `docs/search-space-expansion/debate/claude/claude_debate_lan_3.md`; `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_3.md`.

### 6.2 Adopt ngay

| # | Artifact / Mechanism | Nguồn | Owner đề xuất |
|---|---------------------|-------|---------------|
| 1 | `prelock_authoring_contract.md` (`results_blind`, `compile_only`, `no_runtime_feedback`) | `CL-09` + `CL-11` + Codex/Claude/ChatGPT Pro round 3 | 006 + 015 |
| 2 | `generation_mode` state machine với `conditional_cold_start` law (`grammar_depth1_seed` mandatory only when seed registry empty) | `OI-03` round 4 | 006 + 003 |
| 3 | `feature_lineage.jsonl` + `candidate_genealogy.jsonl` + `proposal_provenance.json` | `CL-12` | 015 + 006 |
| 4 | `descriptor_core_v1.md` với 4 mandatory cell axes + annotation fields | `OI-08` round 4 | 006 + 017 |
| 5 | `breadth_activation_contract.md` (`comparison_domain`, `equivalence_method`, `scan_phase_correction_method`, `minimum_robustness_bundle`) | `CL-13` | 013 + 017 + 008 + 003 |
| 6 | `proof_bundle_minimum_v1.md` (nearest-rival audit, plateau/stability, cost sensitivity, dependency stressor, contradiction profile when needed) | `OI-05` round 4 | 017 + 013 + 015 |
| 7 | `contradiction_registry.json` (descriptor-level, shadow-only) | `CL-10` + `X38-ESP-02` | 017 + 015 |

### 6.3 Defer

| # | Artifact / Mechanism | Nguồn | Lý do defer |
|---|---------------------|-------|-------------|
| 1 | Exact default correction formula (`Holm` / `FDR` / `cascade` / hybrid) | `NEW-01` residual | Coupling đã chốt, nhưng evidence chưa đủ để freeze công thức mặc định ở topic này |
| 2 | `GFS depth 2/3`, exhaustive higher-order mutation | Claude/Gemini earlier proposals | Compute + multiplicity + invalidation risk vẫn cao hơn contract maturity của v1 |
| 3 | `APE` code generation | Claude earlier proposal | `parameter_sweep` nếu có chỉ là config perturbation; codegen vẫn vượt quá correctness budget của v1 |
| 4 | Domain catalog / CDAP như core architecture | Gemini / Claude | Giá trị provenance có thật, nhưng không giải critical-path gap của v1 |
| 5 | Full EPC lifecycle / activation ladder vượt shadow-only | Codex / Claude | `MK-17` giữ same-dataset activation inert; v1 chỉ cần storage/registry shadow-only |
| 6 | Exact numerical thresholds cho surprise/equivalence/correction | Claude / Gemini / earlier ChatGPT Pro | Cần do `013/017` chốt sau khi interface bundle đã freeze |

### 6.4 Ownership tạm

| Topic | Gánh gì |
|-------|---------|
| 006 | Producer semantics, operator grammar, compile-to-manifest, conditional cold-start state machine, feature-level structural pre-bucket |
| 017 | Coverage map, cell-elite archive, local probes, surprise semantics, phenotype/contradiction shadow storage |
| 015 | Lineage/provenance artifacts, field enumeration, invalidation matrix, compile-batch metadata |
| 013 | Common comparison domain, correction-law default, minimum robustness obligations |
| 008 | Identity vocabulary boundary và candidate/system equivalence categories |
| 003 | Stage insertion points, phase gating, breadth activation blocker wiring |

---

## 7. Agenda vòng sau

Nếu round 5 tồn tại, chỉ còn 5 blocker đáng bàn:

- `OI-01` — closure trigger wording để issue rời active register
- `OI-03` — exact state machine condition cho `conditional_cold_start`
- `OI-05` — nếu muốn phản đối obligation-level proof inventory, phải đưa inventory thay thế hoàn chỉnh
- `OI-08` — có cần nâng `holding_bucket` từ annotation lên mandatory axis không, và structural pre-bucket nên tối thiểu chứa trường nào
- `NEW-01` — exact default correction formula + invalidation cascade

`OI-04` đã `DEFER` cho Topic `015`. `OI-07` đã `CONVERGED`; muốn reopen phải tạo `REOPEN-*` với bằng chứng mới đúng chuẩn `debate/rules.md` §7 và §12. Nếu round 5 không tạo được delta thực chất cho 5 blocker trên, topic này phải chuẩn bị closure bằng `CONVERGED + DEFER`, không được kéo dài bằng cách đổi tên issue cũ.

**Format phản hồi cho agent vòng sau:**

```md
### OI-{NN}
- **Stance**: AGREE / DISAGREE / AMEND
- **Điểm đồng ý**: ...
- **Điểm phản đối**: ...
- **Đề xuất sửa**: ...
- **Evidence**: {file path hoặc finding ID}
```

Riêng `NEW-01`, nếu phản đối `paired_daily_returns_after_costs` hoặc phản đối việc phải freeze `scan_phase_correction_method` trước breadth activation, bên phản biện phải đưa **contract thay thế hoàn chỉnh**. Không chấp nhận phản hồi kiểu “để topic sau” vì `CL-13` đã khóa coupling ở mức kiến trúc.

---

## 8. Change Log

| Vòng | Ngày | Agent | Tóm tắt thay đổi |
|------|------|-------|-------------------|
| 3 | 2026-03-26 | ChatGPT Pro | Thêm `CL-09`/`CL-10`; đẩy `grammar_depth1_seed` thành default cold-start path; đề xuất `NEW-01` với candidate contract cụ thể. |
| 4 | 2026-03-26 | ChatGPT Pro | Thêm `CL-11`/`CL-12`/`CL-13`; chuyển `OI-07` sang `CONVERGED`, `OI-04` sang `DEFER`; sửa overreach của round 3 bằng cách bỏ yêu cầu freeze sớm `Holm` default; thay `mandatory vs optional` bằng `conditional cold-start law`. |

---

**Status Table (required by `debate/rules.md` §11)**

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| OI-01 | Owner split cho pre-lock generation lane | Thiếu sót | PARTIAL | “Nếu không có physical script owner ngay bây giờ thì pipeline orchestration sẽ sụp.” | Search-space-expansion phải khóa contract ownership; file/CLI entrypoint là downstream implementation của `003` sau khi `006/015` đóng. |
| OI-03 | Cold-start producer law | Thiếu sót | PARTIAL | “Depth-1 phải luôn mandatory” / “Depth-1 nên luôn optional” | Cả hai đều sai object; rule đúng là conditional theo trạng thái declared registry/seed manifest tại protocol lock. |
| OI-04 | Residual field list + invalidation matrix | Thiếu sót | DEFER | “Split provenance vẫn còn là tranh chấp kiến trúc.” | Không còn; semantic split đã hội tụ. Residual chỉ còn enumeration/invalidation thuộc Topic `015`. |
| OI-05 | Minimum recognition/proof inventory | Thiếu sót | PARTIAL | “Chưa freeze numeric threshold thì chưa thể khóa inventory.” | Inventory obligation và numeric threshold là hai tầng khác nhau; tầng đầu đủ evidence để khóa, tầng sau thì chưa. |
| OI-07 | Domain-seed / cross-domain hook | Judgment call | CONVERGED | “Domain catalog phải là core engine vì VDO đến từ cảm hứng cross-domain.” | VDO value đến từ composition, không đến từ session/domain metaphor; provenance hook giữ trail mà không tạo architectural dependency. |
| OI-08 | Cell axes + equivalence interface | Thiếu sót | PARTIAL | “AST-hash + parameter distance là đủ cho equivalence.” | Đó chỉ là structural sameness; candidate/system equivalence cần behavioral audit trên common comparison domain. |
| NEW-01 | Default correction law + invalidation cascade | Thiếu sót | PARTIAL | “Đã biết breadth phải đi cùng correction thì nên khóa luôn `Holm` default.” | Coupling đã hội tụ, nhưng exact formula chưa có evidence đủ mạnh; phải mở residual này cho `013`/round sau chốt. |
