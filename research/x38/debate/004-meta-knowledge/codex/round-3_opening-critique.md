# Round 3 Opening Critique — Codex (Stage 1B)

**Topic**: 004 — Meta-Knowledge Governance  
**Reviewer**: codex  
**Date**: 2026-03-21  
**Scope**: Stage 1B — `MK-08`→`MK-15` + `C3`→`C6`

---

## Artifacts Read

- `debate/rules.md`
- `debate/debate-index.md`
- `x38_RULES.md`
- `docs/design_brief.md`
- `docs/evidence_coverage.md`
- `docs/v6_v7_spec_patterns.md`
- `debate/004-meta-knowledge/findings-under-review.md`
- `debate/004-meta-knowledge/input_solution_proposal.md`
- `debate/004-meta-knowledge/input_proposal_critique.md`
- `debate/004-meta-knowledge/claude_code/round-3_author-reply.md`
- `research/x37/docs/gen1/RESEARCH_PROMPT_V8/PROMPT_FOR_V8_HANDOFF.md` [extra-archive]
- `research/x37/docs/gen1/RESEARCH_PROMPT_V8/CONVERGENCE_STATUS_V3.md` [extra-archive]

## Mandatory Rule Reminder

1. `§4`: Tôi tấn công argument, không tấn công kết luận. Nếu kết luận có thể đúng nhưng lý do đang được dùng sai, tôi bác bỏ lý do đó.
2. `§7`: Tôi không đánh dấu `Converged` trong file này. Round mở đầu chưa có steel-man `(a)(b)(c)`.
3. `§8`: Tôi không dùng ngôn ngữ nhượng bộ mềm. Mọi đồng ý hay bác bỏ đều phải gắn vào evidence cụ thể.
4. `§12`: Tôi không mở topic mới. Mọi điểm dưới đây đều nằm trong scope Stage 1B hiện tại.

## Stage 1B Baseline

Ba constraint đã chốt ở Stage 1A làm thay đổi shape của Stage 1B:

1. `Same dataset` => empirical priors `shadow-only` pre-freeze; chỉ Tier 1 axioms active (`docs/design_brief.md:87-89`, `debate/004-meta-knowledge/findings-under-review.md:843-876`, `debate/004-meta-knowledge/claude_code/round-3_author-reply.md:190-193`).
2. Compiler chỉ là deterministic constraint validator; artifact phải tách `CONSTRAINT_VALIDATION` khỏi `SEMANTIC_REVIEW` (`debate/004-meta-knowledge/claude_code/round-3_author-reply.md:127-135`, `debate/004-meta-knowledge/claude_code/round-3_author-reply.md:197-198`).
3. Auditor được giữ nhưng criteria downgrade phải reviewable, logged, queryable (`debate/004-meta-knowledge/claude_code/round-3_author-reply.md:161-166`, `debate/004-meta-knowledge/claude_code/round-3_author-reply.md:198`).

Nhiều argument ở `MK-09`/`MK-10`/`MK-14`/`MK-15` và `C3`/`C4`/`C5` chỉ đứng được nếu bỏ qua baseline này.

---

## X38-MK-08 — Lesson Lifecycle

**Target argument**: Proposal §4 trả lời lifecycle chủ yếu bằng actor chain `Search AI -> compiler -> auditor -> human`, rồi kết luận `95% rules không cần human`.

**Classification**: `Thiếu sót`

**Evidence pointers**:

- `debate/004-meta-knowledge/findings-under-review.md:403-443`
- `debate/004-meta-knowledge/input_solution_proposal.md:108-123`
- `debate/004-meta-knowledge/input_solution_proposal.md:225-234`
- `debate/004-meta-knowledge/claude_code/round-3_author-reply.md:127-166`

**Critique**:

1. Proposal đang thay một **org chart** cho một **lifecycle**. Ai làm gì không trả lời object có những state nào, transition nào hợp lệ, transition nào reversible, và artifact nào bắt buộc cho mỗi transition. `MK-08` hỏi đúng vào khoảng trống này (`Creation -> Classification -> Review -> Active -> [Challenge] -> [Modify] -> Retire`), nhưng proposal mới chỉ phân vai actor, chưa định nghĩa state machine.
2. Câu "`95% rules không cần human`" chưa có burden of proof. Sau `D4` và `D9`, mọi rule empirical muốn có force đều phải có semantic artifact reviewable: `Partially` cần structured artifact; downgrade/narrow cần criteria logged. Điều đó không nhất thiết đòi human approve từng rule, nhưng nó bác bỏ argument rằng lifecycle về cơ bản đã được giải xong chỉ bằng asymmetry authority.
3. Proposal chọn `SQLite append-only, versioned`, nhưng lại chưa trả lời câu hỏi cốt lõi của `MK-08`: sửa rule thì `overwrite`, `version chain`, hay `append-only + current pointer`? Chọn storage trước khi chốt transition law là đảo ngược dependency.
4. Sau `D8`, activation không thể là một bit `accepted`. Cần ít nhất tách rõ `CONSTRAINT_VALIDATION=PASS` khỏi `SEMANTIC_REVIEW=PENDING/COMPLETE`; nếu không, lifecycle vẫn collapse classification/review/activation vào một bước ngầm.

---

## X38-MK-09 — Tier 2 Challenge Process

**Target argument**: Challenge có thể được xử lý đủ bằng `challenge bundle` định sẵn + trigger list + conservative default `follow rule, challenge later`.

**Classification**: `Thiếu sót`

**Evidence pointers**:

- `debate/004-meta-knowledge/findings-under-review.md:455-488`
- `debate/004-meta-knowledge/findings-under-review.md:776-831`
- `debate/004-meta-knowledge/input_solution_proposal.md:126-153`
- `debate/004-meta-knowledge/input_solution_proposal.md:318-324`
- `docs/design_brief.md:87-89`

**Critique**:

1. Argument "`follow rule, challenge later` giữ lock discipline" bỏ qua failure mode quan trọng nhất: evidence để challenge **không exogenous**. `MK-16` đã chỉ ra rule đang bị challenge có thể chính là thứ bóp ngân sách và coverage của family cần disconfirm nó. Nếu không gắn challenge với `coverage obligation`, conservative default này có thể trở thành self-sealing ratchet, không phải governance an toàn.
2. `Minimal probe = 1 representative + 1 ablation + 1 paired test` chuẩn hóa paperwork, nhưng chưa chứng minh được **adequacy**. Với family rộng, một representative có thể chỉ chạm vùng yếu nhất của family đó. `MK-16` đã converged rằng sufficiency phải được định nghĩa theo coverage obligation, không phải theo checklist mỏng.
3. `K challenges across M campaigns` là primitive yếu. Một contradiction đủ mạnh và đủ coverage có thể đáng review ngay; ngược lại nhiều probes underpowered không nên cộng dồn thành “evidence” cho override. Đếm challenge trước khi định nghĩa probe sufficiency là đặt metric trước measurement law.
4. Trong `v1` same-dataset, empirical priors là `shadow-only`; vì vậy challenge không phải runtime problem của pre-freeze discovery (`docs/design_brief.md:87-89`, `input_solution_proposal.md:318-324`). Proposal hiện viết challenge như cơ chế trung tâm chung, trong khi baseline đã đẩy phần này sang `v2+`.

---

## X38-MK-10 — Tier 2 Expiry Mechanism

**Target argument**: `half_life = 3 opportunities`, `archive_after = 6`, cộng với `weight decay`, là expiry mechanism đủ operational.

**Classification**: `Thiếu sót`

**Evidence pointers**:

- `debate/004-meta-knowledge/findings-under-review.md:500-518`
- `debate/004-meta-knowledge/findings-under-review.md:573-599`
- `debate/004-meta-knowledge/input_solution_proposal.md:157-168`
- `debate/004-meta-knowledge/claude_code/round-3_author-reply.md:190-198`

**Critique**:

1. Proposal đang đổi tên `numeric confidence` thành `weight decay`. Nếu chưa định nghĩa được `in-scope opportunity`, `refresh`, và `contradiction`, thì `3` và `6` chỉ là threshold arbitrary với lớp sơn mới. `MK-12` đã nêu rõ scalar confidence thiếu trustworthy; expiry không thể lén dựa vào đúng primitive đó.
2. `Automatic narrowing nếu contradicted ngoài scope gốc` là logic đáng ngờ. Evidence ngoài scope gốc nên trigger review về **claim transferability**, không nên tự động rewrite rule trong-scope. Nếu không, framework đang dùng out-of-scope data để silently mutate meaning của rule cũ.
3. Theo `D1`, retirement phải explicit và reversible. Counter hoặc decay có thể tạo `REVIEW_REQUIRED`; nhưng `ACTIVE -> RETIRED/ARCHIVED` không nên là side-effect của việc tụt qua một threshold. Nếu không có transition artifact ghi reason, expiry lại trở về absorption ngầm theo chiều ngược lại.
4. Proposal chưa nói archived rules có thể re-activate thế nào ngoài câu human review “muốn cứu rule đã archive”. Không có reactivation law cụ thể thì `archive` không phải governance state hoàn chỉnh; nó là hố đen.

---

## X38-MK-11 — Conflict Resolution Between Lessons

**Target argument**: `max_active_tier2 = 8` với selection theo `scope match`, `evidence weight`, `suppression risk`, `novelty distance` có thể làm khung giải quyết conflict đủ thực dụng.

**Classification**: `Thiếu sót`

**Evidence pointers**:

- `debate/004-meta-knowledge/findings-under-review.md:530-557`
- `debate/004-meta-knowledge/input_solution_proposal.md:196-205`
- `debate/004-meta-knowledge/input_proposal_critique.md:94-106`
- `debate/004-meta-knowledge/claude_code/round-3_author-reply.md:190-193`

**Critique**:

1. Proposal đang coi **ranking** là **conflict resolution**. Đó là category error. Top-`k` selection chỉ quyết định cái gì được load vào campaign; nó không trả lời hai rule là contradictory, complementary, nested, hay incomparable.
2. Nếu một rule bị loại khỏi active set chỉ vì thua ranking heuristic, framework không để lại artifact nào nói conflict gì đã tồn tại và tại sao precedence đó được chọn. Điều này vi phạm thẳng `D1` auditability: conflict bị che bởi memory budget.
3. `Scope match` cũng chưa đủ làm precedence primitive, vì `D3` mới chỉ chốt rằng `v2+` phải có context declaration schema tối thiểu. Khi context lattice còn chưa spec'd, dùng `scope match` như một số đo đủ mạnh cho conflict resolution là đi trước evidence.
4. `Suppression risk` và `novelty distance` còn tệ hơn: một cái nhập noise từ ratchet logic, một cái đòi biết campaign “novel ở đâu” trước khi discovery bắt đầu. Đây là ranking heuristics cho attention management, không phải model cho contradiction.

---

## X38-MK-12 — Confidence Scoring

**Target argument**: Proposal tránh field `confidence`, nhưng có thể dùng `weight`, `budget_multiplier`, `evidence weight`, và decay thresholds để vận hành Tier 2 một cách đủ principled.

**Classification**: `Judgment call`

**Evidence pointers**:

- `debate/004-meta-knowledge/findings-under-review.md:569-599`
- `debate/004-meta-knowledge/input_solution_proposal.md:165-168`
- `debate/004-meta-knowledge/input_solution_proposal.md:203-205`
- `debate/004-meta-knowledge/input_solution_proposal.md:245-247`
- `debate/004-meta-knowledge/input_proposal_critique.md:58-70`

**Critique**:

1. Proposal về thực chất đã đưa `numeric confidence` quay lại qua cửa sau. `budget_multiplier`, `weight decay`, `evidence weight` đều là scalar tóm tắt cùng một câu hỏi: “rule này đáng ảnh hưởng bao nhiêu?”. Nếu không chứng minh được model phía sau, các scalar này chỉ tạo cảm giác precision giả.
2. Vấn đề confirmation bias trong `MK-12` vẫn còn nguyên: rules được obey -> search bị shape -> rule nhìn như được confirm. Một số `weight` không làm circularity đó biến mất; nó chỉ nén circularity vào một con số khó audit hơn prose.
3. Cách tách sạch hơn là: epistemic state nên là qualitative (`ACTIVE`, `CHALLENGED`, `CONTESTED`, `RETIRED`), còn numeric knobs nếu tồn tại phải được khai báo là **operational defaults**, không được biện minh như “confidence”. Nếu không, governance force và epistemic confidence sẽ lại bị trộn.
4. Vì đây là tradeoff thực sự giữa transparency và control surface, tôi giữ `Judgment call`. Nhưng burden of proof nằm ở bên muốn dùng scalar: họ phải chỉ ra số đó đo cái gì ngoài “độ tự tin chủ quan được mã hóa”.

---

## X38-MK-13 — Storage Format

**Target argument**: `SQLite append-only` làm authoritative store, còn `policy_snapshot.json`, `policy_diff.md`, `rule_proposals.jsonl`, `challenge_outcomes.jsonl` là các view/phụ trợ, là storage split đúng ngay từ đầu.

**Classification**: `Judgment call`

**Evidence pointers**:

- `debate/004-meta-knowledge/findings-under-review.md:620-651`
- `debate/004-meta-knowledge/input_solution_proposal.md:223-234`
- `debate/004-meta-knowledge/input_solution_proposal.md:308-321`
- `docs/v6_v7_spec_patterns.md:276-282`

**Critique**:

1. Stage 1A đã làm rõ attack surface: active pre-freeze rule payload phải gần như hoàn toàn structured; free-text rationale sống trong audit artifacts (`debate/004-meta-knowledge/findings-under-review.md:643-651`). Điều đó tự động loại Markdown/hybrid khỏi vai trò source of truth cho active rules. Debate còn lại không phải `JSON vs Markdown`, mà là `structured snapshot + structured event log` nên materialize bằng gì.
2. Proposal §10 và §13 đang nói hai câu khác nhau. §10 gọi `SQLite append-only` là authoritative ngay bây giờ; §13 lại nói `v1 = JSON files, no database`. Nếu không phân biệt rõ `canonical log` với `runtime snapshot` và `human diff`, thì “authoritative” đang bị dùng mơ hồ.
3. Storage phải theo sau lifecycle. Trước khi `MK-08` chốt được transition law và `D8/D9` chốt artifact semantics, tuyên bố `SQLite` là source of truth là premature optimization ở tầng kiến trúc.
4. `docs/v6_v7_spec_patterns.md:276-282` đúng ở điểm machine-readable snapshot là bắt buộc. Nhưng requirement đó không suy ra database là bắt buộc. Nó chỉ suy ra Markdown-only là không đủ.

---

## X38-MK-14 — Boundary with Contamination Firewall

**Target argument**: Boundary có thể được nắm bằng một contract kiểu `Topic 002 exports ContaminationCheck(lesson) -> CLEAN | CONTAMINATED | AMBIGUOUS`, còn topic 004 export `LessonSpec(...)`.

**Classification**: `Thiếu sót`

**Evidence pointers**:

- `debate/004-meta-knowledge/findings-under-review.md:668-697`
- `docs/design_brief.md:38-55`
- `docs/design_brief.md:87-89`
- `debate/004-meta-knowledge/claude_code/round-3_author-reply.md:98-105`
- `debate/004-meta-knowledge/claude_code/round-3_author-reply.md:127-166`

**Critique**:

1. Argument hiện vẫn quá symmetric. Sau `D7`, topic 002 và topic 004 không phải hai nơi cùng “định nghĩa cái gì được phép”. Topic 002 phải sở hữu admissibility/content gate; topic 004 phải sở hữu governance/lifecycle sau khi object đã admissible. Nếu cả hai cùng encode “allowed lessons” theo ngôn ngữ riêng, ta có double semantics và drift.
2. Ternary output `CLEAN | CONTAMINATED | AMBIGUOUS` là quá nghèo cho boundary thật. Sau `D8` và `D9`, hệ governance còn cần biết object đang `shadow-only`, `review-pending`, hay `eligible-for-activation`. Nếu contract của topic 002 chỉ trả về cleanliness, topic 004 không được phép overload kết quả đó thành lifecycle state.
3. `MK-17` đã làm bài toán v1 đơn giản hơn nhiều: same-dataset empirical priors đều `shadow-only` pre-freeze (`docs/design_brief.md:87-89`). Vì vậy hard boundary hiện tại không phải “overlap nào đủ để shadow?”, mà là “payload nào admissible cho runtime, payload nào chỉ là audit memory”. Proposal chưa tận dụng simplification này đủ mạnh.
4. Tôi giữ issue là `Thiếu sót` chứ không phải `Judgment call`, vì ở đây thiếu một interface decomposition rõ ràng hơn là thiếu một preference.

---

## X38-MK-15 — Bootstrap Problem

**Target argument**: Bootstrap phải được chọn giữa các option gần như monolithic: start from zero, seed V4-V8, seed Tier 1 only, hoặc tạo `LEGACY` tier/subtype.

**Classification**: `Judgment call`

**Evidence pointers**:

- `debate/004-meta-knowledge/findings-under-review.md:712-762`
- `debate/004-meta-knowledge/input_solution_proposal.md:209-219`
- `debate/004-meta-knowledge/input_solution_proposal.md:308-324`
- `docs/design_brief.md:87-89`
- `docs/design_brief.md:107-118`
- `research/x37/docs/gen1/RESEARCH_PROMPT_V8/CONVERGENCE_STATUS_V3.md:5-10` [extra-archive]
- `research/x37/docs/gen1/RESEARCH_PROMPT_V8/CONVERGENCE_STATUS_V3.md:138-145` [extra-archive]

**Critique**:

1. Option framing đang trộn hai câu hỏi khác nhau: `seed vào registry cái gì?` và `thứ đó có được shape discovery pre-freeze không?` Sau `MK-17`, câu hỏi thứ hai đã được chốt cho same-dataset mode: empirical priors có thể tồn tại, nhưng `shadow-only`. Vì vậy bootstrap không còn là chọn `A/B/C/D` một cục như finding đang trình bày.
2. Proposal migration §9 đi đúng nửa đường khi nói legacy mặc định vào `Tier 3` hoặc `Tier 2-narrow`, có provenance, overlap guard, challenge, expiry. Nhưng ngay sau đó nó lại đề xuất `3 campaign đầu challenge budget 25-30%`, tức là giả định legacy empirical priors sẽ tham gia runtime. Điều này mâu thuẫn với chính §13 `v1` scope (`Tier 1 active; empirical shadow-only`).
3. `LEGACY` như tier thứ tư có vẻ over-encoding. Cái cần phân biệt không phải power class mới, mà là provenance class: `source = online_v4_v8`, `same_dataset_lineage = true`, `activation_requires_new_data = true`. Metadata đủ để diễn đạt mà không phá `D5`.
4. Đây là `Judgment call` vì tradeoff thật nằm ở mức seed bao nhiêu audit memory để giảm waste ở ngày đầu, chứ không còn nằm ở quyền influence pre-freeze trên cùng dataset.

---

## C3 — Budget Split 70/20/10 Arbitrary

**Target argument**: C3 đúng khi đòi bỏ split cố định và chuyển sang adaptive budget theo việc challenge probes “consistently produce nothing” hay “consistently surprise”.

**Classification**: `Thiếu sót`

**Evidence pointers**:

- `debate/004-meta-knowledge/input_proposal_critique.md:58-70`
- `debate/004-meta-knowledge/findings-under-review.md:806-831`
- `debate/004-meta-knowledge/input_solution_proposal.md:137-142`
- `debate/004-meta-knowledge/input_solution_proposal.md:318-324`
- `docs/design_brief.md:87-89`

**Critique**:

1. C3 đúng ở điểm phủ nhận `70/20/10` như hằng số kiến trúc. Nhưng fix của C3 vẫn coi budget là proxy cho confidence, chỉ khác ở chỗ số này được cập nhật bằng feedback loop. Đó vẫn là meta-circularity.
2. `Probes consistently produce nothing` không phải signal có nghĩa nếu probe sufficiency chưa chốt. Một probe underpowered “không thấy gì” có thể chỉ phản ánh coverage tệ, không phản ánh rule đúng. `MK-16` đã converged rằng sufficiency phải neo vào coverage obligation, không phải outcome frequency.
3. Same-dataset `v1` còn đơn giản hơn nữa: không có frontier/probe split cho empirical priors vì chúng không active pre-freeze (`docs/design_brief.md:87-89`, `input_solution_proposal.md:318-324`). Vì vậy sharper critique không phải “fixed hay adaptive”, mà là “đây không phải v1 architecture question”.
4. Nếu budget split quay lại ở `v2+`, burden of proof phải chuyển từ “adaptive feels better” sang “split này bảo toàn đủ disconfirming coverage cho suppressed families”.

---

## C4 — Overlap Guard Quá Mạnh

**Target argument**: Overlap guard chỉ nên áp dụng cho `evaluation data overlap`; training/warmup overlap vẫn có thể cho Tier 2 rule active trên phần non-overlapping evaluation.

**Classification**: `Sai thiết kế`

**Evidence pointers**:

- `debate/004-meta-knowledge/input_proposal_critique.md:74-90`
- `docs/design_brief.md:87-89`
- `docs/design_brief.md:107-145`
- `debate/004-meta-knowledge/findings-under-review.md:853-876`
- `research/x37/docs/gen1/RESEARCH_PROMPT_V8/CONVERGENCE_STATUS_V3.md:9-10` [extra-archive]
- `research/x37/docs/gen1/RESEARCH_PROMPT_V8/CONVERGENCE_STATUS_V3.md:138-145` [extra-archive]

**Critique**:

1. C4 đang mở lại một decision đã chốt. `MK-17` và `design_brief` không nói “shadow nếu overlap evaluation đủ lớn”; chúng nói trên same dataset, empirical cross-campaign priors là `shadow-only` pre-freeze. Điểm này được chốt để chặn contamination qua governance channel, không chỉ qua eval labels.
2. Argument của C4 giả định contamination chỉ đến từ overlapping evaluation outcomes. `MK-02`/`D2` đã bác premise đó: structural priors học từ cùng file đã đủ để bias search, ngay cả khi evaluation window tương lai không overlap trọn vẹn. Training/warmup overlap không “vô hại” ở đây, vì lesson đã được học trên cùng lineage dữ liệu.
3. `Active cho non-overlapping portion` còn trộn lẫn hai phase mà brief cố tình tách: same-dataset re-derivation vs genuinely new data / clean OOS / extended-data research (`docs/design_brief.md:107-145`). Nếu đã có appended data mới và muốn activate priors, đó là câu chuyện `new dataset / v2+`, không phải loophole trong same-file mode.
4. Vì C4 tấn công trực tiếp boundary resolved ở `MK-17`, tôi xếp nó là `Sai thiết kế`, không phải refinement hợp lý.

---

## C5 — Active Cap Selection = Pre-Campaign Bias

**Target argument**: Bỏ `novelty distance`, giữ `scope match + evidence weight`, rồi lấy top-8 là đủ để giải bài toán active set.

**Classification**: `Thiếu sót`

**Evidence pointers**:

- `debate/004-meta-knowledge/input_proposal_critique.md:94-106`
- `debate/004-meta-knowledge/input_solution_proposal.md:196-205`
- `debate/004-meta-knowledge/input_solution_proposal.md:319-320`
- `debate/004-meta-knowledge/findings-under-review.md:530-557`
- `debate/004-meta-knowledge/findings-under-review.md:853-859`

**Critique**:

1. C5 đúng khi bác `novelty distance`; metric đó là circular. Nhưng fix của C5 vẫn giữ assumption sai hơn: active-cap ranking có thể đóng vai conflict resolver. `Top 8 by scope/evidence` vẫn là pre-campaign bias, chỉ là bias có vẻ clean hơn.
2. `Evidence weight` không neutral. Nó có thể đã hấp thụ obedience bias, stale confirmations, và selection effects mà `MK-12` cảnh báo. Thay `novelty distance` bằng `evidence weight` không biến top-`k` thành cơ chế công bằng.
3. `MK-17` còn làm critique này hẹp hơn: trong same-dataset `v1`, active cap không cần thiết. Câu hỏi thật chỉ xuất hiện ở `v2+`, sau khi context schema và conflict model được định nghĩa. Nếu chưa có hai thứ đó, top-8 selection vẫn là heuristic đứng trên nền chưa tồn tại.
4. Vì vậy C5 là critique đúng một nửa: nó diệt được một heuristic tệ, nhưng chưa chạm lỗi gốc là đang dùng attention budget mechanism để giải semantic conflict.

---

## C6 — Complexity Tổng Thể Quá Nhiều Cho V1

**Target argument**: C6 đúng khi đề xuất v1/v2/v3 rollout, trong đó `v1 (BTC only)` vẫn giữ `overlap guard + challenge probes`, chỉ bỏ database.

**Classification**: `Thiếu sót`

**Evidence pointers**:

- `debate/004-meta-knowledge/input_proposal_critique.md:110-127`
- `debate/004-meta-knowledge/input_solution_proposal.md:308-324`
- `docs/design_brief.md:87-89`
- `debate/004-meta-knowledge/claude_code/round-3_author-reply.md:190-198`

**Critique**:

1. Direction của C6 là đúng: phải stage complexity. Nhưng v1 cutline mà C6 đề xuất vẫn còn quá to. Nếu same-dataset empirical priors đã `shadow-only`, thì `challenge probes`, `active cap`, và phần lớn `overlap guard` không phải v1 runtime surface nữa.
2. Proposal §13 thực ra đã có cutline tốt hơn C6: `Tier 1 axioms active`, empirical stored for audit only, JSON files, no database. C6 chưa khai thác full consequence của `MK-17`, nên vẫn để lại nhiều machinery không tạo value trong BTC-only single-snapshot v1.
3. Điều không nên defer là `D1`, `D8`, `D9`. Ta có thể defer runtime machinery, nhưng không thể defer explicit transition law, artifact separation, hay auditor criteria. Nếu không, v1 sẽ đơn giản bằng cách quay lại honor system, tức là lặp đúng failure mode cũ.
4. Critique đúng hơn phải là: `stage runtime complexity aggressively, but freeze governance invariants now`. C6 mới nói được nửa đầu.

---

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|----------|-------|-----------|------------|---------------------|----------------------|
| X38-MK-08 | Lesson lifecycle | Thiếu sót | Open | Chưa thực hiện `§7` | — |
| X38-MK-09 | Tier 2 challenge process | Thiếu sót | Open | Chưa thực hiện `§7` | — |
| X38-MK-10 | Tier 2 expiry mechanism | Thiếu sót | Open | Chưa thực hiện `§7` | — |
| X38-MK-11 | Conflict resolution between lessons | Thiếu sót | Open | Chưa thực hiện `§7` | — |
| X38-MK-12 | Confidence scoring — numeric vs qualitative | Judgment call | Open | Chưa thực hiện `§7` | — |
| X38-MK-13 | Storage format | Judgment call | Open | Chưa thực hiện `§7` | — |
| X38-MK-14 | Boundary with Contamination Firewall | Thiếu sót | Open | Chưa thực hiện `§7` | — |
| X38-MK-15 | Bootstrap problem | Judgment call | Open | Chưa thực hiện `§7` | — |
| C3 | Budget split 70/20/10 arbitrary | Thiếu sót | Open | Chưa thực hiện `§7` | — |
| C4 | Overlap guard quá mạnh | Sai thiết kế | Open | Chưa thực hiện `§7` | — |
| C5 | Active cap selection = pre-campaign bias | Thiếu sót | Open | Chưa thực hiện `§7` | — |
| C6 | Complexity tổng thể quá nhiều cho v1 | Thiếu sót | Open | Chưa thực hiện `§7` | — |
