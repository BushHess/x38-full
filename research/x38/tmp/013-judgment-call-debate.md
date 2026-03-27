Round 1: Nhận định của Claude Code:

Tình trạng Topic 013 — Convergence Analysis
Path: /var/www/trading-bots/btc-spot-dev/research/x38/debate/013-convergence-analysis;

6 rounds đã hoàn tất (cả hai bên đều có round 6) — đây là giới hạn max_rounds_per_topic theo §13.

Kết quả cuối cùng (round 6, cả hai bên đồng ý):
Issue	Status	Ghi chú
CA-01	Judgment call	Cả hai bên đồng ý: metric law (Kendall's W) đã frozen, dispute còn lại là scope ownership (013 chỉ own measurement hay cả convergence-to-action threshold?)
CA-02	Judgment call	Cả hai bên đồng ý: stop-law structure tồn tại, dispute còn lại là governance bootstrap (provisional defaults vs evidence-backed constants)
SSE-09	Judgment call	Cả hai bên đồng ý: v1 default = Holm, BH = upgrade path. Dispute còn lại chỉ là exact calibration constants (α=0.05, q=0.10)
SSE-04-THR	Judgment call	Contamination subpoint Converged. Dispute còn lại: items 1-2 (ρ>0.95, hash) frozen by author nhưng chưa source-backed. Items 3-4 blocked by Topic 017.
Nhận xét chất lượng debate
Debate đã productive: Từ blank proposal → frozen Kendall's W metric, 4-level convergence structure, Holm default, behavioral ρ threshold, AST hash spec. Nhiều concession evidence-backed từ cả hai bên.

Parity đạt: Round 6 có cả author reply và reviewer reply. §14b satisfied.

4/4 issues đều là Judgment call — điều kiện tiên quyết cho closure đã đạt (§14: "mọi issue còn Open phải chuyển thành Judgment call").

Codex round 6 chất lượng tốt: Thực hiện steel-man đúng (SSE-09), framing rõ ràng cho từng Judgment call (Position A vs Position B), không false convergence.

Bước tiếp theo
Cần làm ngay: Human researcher quyết định 4 Judgment calls → viết final-resolution.md

Theo workflow trong prompt_template.md:

Human researcher quyết định từng Judgment call (§15: decision_owner mặc định là human researcher)
Tạo final-resolution.md theo Template D
Cập nhật findings-under-review.md, debate-index.md, README.md
Tạo/cập nhật draft spec trong drafts/
Các quyết định cần đưa ra:
CA-01: Position A (013 chỉ own measurement law, governance routing thuộc 001×003) hay Position B (013 phải freeze luôn convergence threshold)?

Khuynh hướng tự nhiên: Position A — vì 013 đã tạo computable procedure, governance routing là cross-topic integration.
CA-02: Position A (provisional defaults + human override) hay Position B (chờ offline calibration evidence)?

Khuynh hướng tự nhiên: Position A — bootstrap problem là thực, CONV:UNCALIBRATED label đã có precedent trong repo.
SSE-09: Position A (freeze α=0.05/q=0.10 as conventional) hay Position B (freeze chỉ "Holm default" + leave exact constant to human)?

Khuynh hướng tự nhiên: Position A — conventional thresholds, đã align với existing validation/thresholds.py.
SSE-04-THR: Position A (close items 1-2 now, carry 3-4 as 013×017 obligations) hay Position B (require full surface closed)?

Khuynh hướng tự nhiên: Position A — items 3-4 genuinely blocked by 017, 013 không thể unilateral.

========

Round 2: Ý kiến của ChatGPT Pro

Tôi đã kiểm tra trực tiếp topic 013 trong repo. Theo rules.md, topic đã chạm max_rounds_per_topic = 6; sau mốc này, mọi issue còn Open phải chuyển thành Judgment call, và trước khi đóng phải có parity round. Thư mục claude_code/ và codex/ đều đã có đủ round 1→6, và codex round 6 cũng xác nhận đây là parity round cuối trước khi chuyển sang human judgment. Topic 013 hiện vẫn đang OPEN.

Kết luận của tôi: chốt A / A / A / A, nhưng CA-01 phải viết lại cho đúng boundary ownership, còn SSE-04-THR phải đóng theo kiểu “freeze phần 013 own được, carry-forward phần 017 own” thay vì giả vờ end-to-end complete. Các tranh chấp còn lại không còn là tranh cãi toán học lõi; chúng là tranh chấp về ownership, bootstrap governance và closure discipline.

1) X38-CA-01 — chọn Position A, nhưng sửa câu chữ cho chặt.
Đừng ghi “013 chỉ own measurement law” theo nghĩa hẹp. Câu đúng nên là: Topic 013 owns convergence measurement law, numeric category boundaries, và exported convergence-state / stall outputs; downstream action routing (continue, HANDOFF, Clean OOS) thuộc integration boundary của 001 + 003 + 010. Lý do: 013 đúng là topic đo convergence và stop conditions; F-30 nêu luôn câu hỏi “PARTIALLY_CONVERGED có đủ để move forward không?”, nhưng 001 đã freeze HANDOFF vocabulary/routing contract, 003 owns pipeline integration, còn 010 owns Clean OOS as Phase 2. Ngay reviewer round 6 cũng thừa nhận phần còn lại của CA-01 chỉ còn là dispute về scope ownership, không phải metric bị sai hay còn trống.

Câu chốt để đưa vào final-resolution.md: “Judgment call — Accepted Position A (clarified): Topic 013 closes by freezing convergence measurement law, category thresholds, and exported convergence-state/stall outputs. Downstream routing and certification actions are consumed by Topics 001, 003, and 010.”

2) X38-CA-02 — chọn Position A.
Tôi khuyên freeze luôn v1 stop law và bootstrap defaults: |ΔW_N| < ε_noise trong M session liên tiếp, với ε_cost = ε_noise mặc định cho v1, và bộ default same_data_ceiling = 3 campaigns, S_min = 3, S_max = 5, M = 2. Nhưng phải ghi cực rõ đây là bootstrap defaults / provisional / human-overridable / cần recalibration sau khi có offline evidence thật, chứ không được trình bày như evidence-backed constants. Round 6 của cả hai bên đã thu hẹp tranh chấp CA-02 đúng về điểm này: stop-law structure đã tồn tại; phần còn lại chỉ là có cho phép ship v1 bằng provisional defaults hay phải chờ calibration evidence. online_vs_offline.md cũng nói rất rõ gen1/gen3/gen4 chỉ là evidence về vấn đề, không phải template cho offline constants; ngược lại, validation/thresholds.py cho thấy repo đã có precedent cho fixed thresholds với provenance classes như CONV / CONV:UNCALIBRATED.

Một note bắt buộc nên thêm: nếu Topic 017 sau này đóng coverage floor mà campaign chưa đạt coverage obligation, coverage obligation được quyền trì hoãn stop suggestion; vì chính 013 và 017 đều đã ghi nhận interaction này ở cross-topic tension.

Câu chốt để đưa vào final-resolution.md: “Judgment call — Accepted Position A: v1 freezes the stop-law structure and bootstrap defaults {same_data_ceiling=3, S_min=3, S_max=5, M=2, ε_cost=ε_noise}, explicitly marked provisional / human-overridable / recalibration-required after first genuine offline evidence.”

3) X38-SSE-09 — chọn Position A.
Freeze thẳng: v1 default = Holm, Holm α = 0.05, và BH q = 0.10 là documented upgrade path chỉ kích hoạt khi Topic 017 thực sự đóng được proof-consumption guarantee. 018 đã route exact correction formula xuống 013; 013’s own finding nói rõ topic này own ba việc: default formula, v1 default, và threshold calibration methodology. Reviewer round 6 đã chấp nhận phần cốt lõi là Holm là present operational v1 answer; phần chưa converged chỉ còn là exact constants chưa uniquely derived từ record. Ở đây bạn chính là human decision owner theo §15, nên để trống constants sẽ chỉ làm 013 tiếp tục underspecified. Cách đúng là freeze chúng như fixed conventional v1 constants, không giả vờ đó là x38-calibrated evidence.

Câu chốt để đưa vào final-resolution.md: “Judgment call — Accepted Position A: v1 default is Holm at α = 0.05; BH at q = 0.10 is the documented upgrade path, activated only after Topic 017 closes the required proof-consumption guarantee. These are fixed conventional v1 constants, not x38-derived calibration.”

4) X38-SSE-04-THR — chọn Position A.
Đây là issue cần đóng kiểu chuẩn nhất. Contamination subpoint đã converged rồi; phần còn lại nên chốt như sau: freeze ngay item 1 và item 2 ở authority của human judgment, còn item 3 và item 4 chuyển thành explicit 013×017 integration obligations. Cụ thể, tôi khuyên freeze v1 local semantics là ρ > 0.95 cho behavioral equivalence, và structural hash granularity = normalized AST của signal-generation logic + parameter schema (names/types), loại parameter values ra khỏi hash bucket. Cách này khớp với split đã frozen ở 018/008: 008 owns interface + structural pre-bucket fields, 013 owns equivalence semantics, 017 owns consumption. 017’s own routed issue cũng nói thẳng họ own anomaly thresholds và proof-bundle consumption rules; vì vậy buộc 013 phải đóng end-to-end cả 4 items mới được close là sai ownership boundary. Reviewer round 6 cũng công nhận objection của author về items 3-4 là có thật.

Điểm cần ghi cho công bằng: items 1-2 ở đây là frozen by human judgment as working v1 semantics, không phải “đã source-backed tới mức converged”. Nhưng đó vẫn là quyết định đúng hơn hẳn Position B, vì Position B ép 013 phải quyết các surface mà 017 đã claim ownership.

Câu chốt để đưa vào final-resolution.md: “Judgment call — Accepted Position A: freeze local v1 semantics now (ρ > 0.95; structural pre-bucket granularity = normalized AST of signal-generation logic + parameter schema, excluding parameter values). Carry robustness-bundle minimum numerics and anomaly-axis thresholds as explicit 013×017 integration obligations. Contamination subpoint remains Converged.”

Điểm cuối cùng: trong final-resolution.md, đừng viết kiểu “sẽ giải quyết sau khi 017 đóng” rồi bỏ lửng. Hãy đóng Topic 013 ngay bây giờ, nhưng thêm một mục “Deferred, not blocked” theo đúng tinh thần mà Topic 001 và Topic 018 đã dùng: CA-01 defer downstream routing sang 001/003/010; SSE-04-THR defer items 3-4 sang 013×017; CA-02 ghi review gate cho lần recalibration đầu tiên. Cách này sạch, đúng ownership, và không tạo false completeness.

========

Round 3: Claude Code (phản biện Round 1 + Round 2)

## Đánh giá tổng thể

Cả Round 1 (Claude Code sơ bộ) và Round 2 (ChatGPT Pro) đều chốt A/A/A/A.
Tôi cũng đồng ý hướng A/A/A/A là đúng, nhưng cần chỉ ra 5 điểm mà hai
vòng trước hoặc bỏ qua, hoặc phân tích chưa đủ sắc, hoặc chấp nhận quá dễ
dãi. Tôi sẽ đi từng issue.

---

### 1) CA-01 — Đồng ý Position A, nhưng phản bác cách framing của cả hai vòng trước

**Điểm đồng ý**: 013 đã sản xuất một computable procedure thật sự (Kendall's W,
null distribution law, 4-level structure). K-dependency là sequential dependency,
không phải deferral. Governance routing (PARTIALLY_CONVERGED → action nào?)
đúng là cross-topic 001×003×013.

**Phản bác Round 1**: Round 1 nói "governance routing là cross-topic integration"
nhưng không giải thích TẠI SAO. Chỉ lặp lại position của author mà không
independent reasoning.

**Phản bác Round 2**: ChatGPT Pro thêm "exported convergence-state / stall
outputs" vào scope của 013 — đây là bổ sung đúng. Nhưng ChatGPT Pro né tránh
câu hỏi khó nhất mà Codex đặt ra: Topic 001 line 168 ghi rõ ràng "stop
thresholds, same-data ceiling, sessions-per-campaign → Topic 013". Phrase "stop
thresholds" có thể hiểu là (a) the statistical noise floor τ_low, HOẶC (b) the
substantive governance threshold "bao nhiêu W là đủ để act". Codex hiểu theo
nghĩa (b). Author hiểu theo nghĩa (a). Cả Round 1 lẫn Round 2 đều không
phân tích sự mơ hồ này — chỉ chọn interpretation (a) rồi move on.

**Lập luận của tôi cho Position A (dù thừa nhận ambiguity)**: Ngay cả khi đọc
"stop thresholds" theo nghĩa rộng nhất, câu trả lời "bao nhiêu W là đủ" phụ
thuộc vào COST OF CONTINUING (thuộc protocol/003) và COST OF FALSE STOP (thuộc
001's HANDOFF/010's Clean OOS). 013 có thể cung cấp statistical bounds
(dưới τ_low = noise, trên τ_high = near-identical), nhưng threshold TRONG range
đó là decision theory, không phải measurement theory. Đây là lý do structural
— không phải vì "013 đã làm đủ rồi" mà vì "the answer genuinely requires inputs
013 doesn't own." Topic 001 routed the question; answer crosses boundaries.

**Câu chốt tôi đề xuất** (sửa so với Round 2):

> "Topic 013 freezes: measurement law (Kendall's W), derivation procedure
> (null distribution → τ_low, τ_high), multi-level categories
> (NOT/PARTIALLY/FULLY_CONVERGED), and exported convergence-state output.
> The substantive governance threshold within [τ_low, τ_high] — what
> convergence level triggers what action — is a decision-theoretic question
> requiring cost inputs from 001 (HANDOFF cost), 003 (protocol continuation
> cost), and 010 (Clean OOS certification). This is a 001×003×010×013
> integration obligation, not a 013-internal deliverable."

Sự khác biệt so với Round 2: tôi ghi rõ LÝ DO structural tại sao governance
threshold không thuộc 013, thay vì chỉ nói "downstream routing thuộc 001+003+010."

---

### 2) CA-02 — Đồng ý Position A, nhưng M=2 là mắt xích yếu nhất

**Điểm đồng ý**: Bootstrap problem là thực. Provisional defaults với
CONV:UNCALIBRATED label là cách duy nhất khả thi. ε_cost = ε_noise cho v1
là sạch.

**Phản bác Round 2**: ChatGPT Pro chấp nhận bộ {ceiling=3, S_min=3, S_max=5,
M=2} như một khối thống nhất mà không scrutinize từng số. Tôi thấy M=2 cần
được đặt câu hỏi riêng:

- Với S_min=3, ΔW observation đầu tiên đến sau session 3. Observation thứ hai
  sau session 4. M=2 yêu cầu CẢ HAI đều dưới threshold → stop sớm nhất là
  session 4, chỉ 1 session sau S_min.
- Với S_max=5, observation window = {session 3, 4, 5} → tối đa 3 observations.
  M=2 chỉ cần 2 liên tiếp trong 3 → tỷ lệ false-stop khá cao nếu ε_noise
  không conservative.
- Tại sao M=2 mà không phải M=3? Claude Code round 6 không justify cụ thể
  con số 2. ChatGPT Pro round 2 cũng không hỏi. Lập luận ngầm là: M=3 yêu cầu
  S_max≥6 (vì cần 3 consecutive observations bắt đầu từ session 3), vượt S_max=5.
  Vậy M=2 được chọn vì nó là giá trị lớn nhất compatible với S_max=5.

**Vấn đề thật**: Chain suy luận là V4→V8 ≈ 5 sessions → S_max=5 → M≤3 →
nhưng cần ít nhất 1 "second chance" → M=2. Toàn bộ chain đều là
paradigm-inference. Codex đúng về điểm này. Nhưng Position B (chờ evidence)
không khả thi hơn — bạn cần numbers để start running, và running mới cho
evidence.

**Khuyến nghị bổ sung**: final-resolution.md nên ghi explicit rằng M=2 là
CONSTRAINED CHOICE (bị giới hạn bởi S_max=5), không phải independently justified.
Nếu future evidence cho thấy S_max nên tăng, M cũng cần re-evaluate. Hai số
này coupled, không độc lập.

---

### 3) SSE-09 — Đồng ý Position A, nhưng cần ghi rõ một asymmetry

**Điểm đồng ý**: v1 = Holm. α=0.05 và q=0.10 là conventional. Freeze luôn.

**Phản bác Round 1 và Round 2**: Cả hai vòng trước đều nói "align với existing
validation/thresholds.py" nhưng thực ra có một asymmetry cần acknowledge:
- validation/thresholds.py dùng α=0.10 cho per-test significance
- 013 đề xuất α=0.05 cho Holm FWER — conservative HƠN gấp đôi

Đây KHÔNG phải inconsistency — Claude Code round 6 đã justify đúng: FWER
controls probability of ANY false rejection across entire family, nên phải
stricter hơn per-test. Nhưng Round 1 và Round 2 đều frame nó như "đã align"
mà không note sự khác biệt. Codex có thể (đúng) argue: nếu project đã chọn
α=0.10 làm significance standard, tại sao Holm không cũng dùng 0.10? Câu trả
lời: vì FWER compounds — một false positive trong scan phase có thể redirect
toàn bộ probe budget của một cell (Codex round 5 đã identify đúng distortion
mechanism này). Nhưng argument này nên được ghi rõ trong final-resolution.md
thay vì giả vờ 0.05 và 0.10 "align" với nhau.

**Câu chốt tôi đề xuất** (bổ sung so với Round 2):

> "v1 default = Holm at α_FWER = 0.05 (stricter than per-test α = 0.10 because
> family-wise errors compound across scan phase — one false discovery can
> redirect an entire cell's probe budget). BH at q_FDR = 0.10 is the
> documented upgrade path, matching the project's per-test α. These are fixed
> conventional v1 constants; adaptive calibration is v2+ scope."

---

### 4) SSE-04-THR — Đồng ý Position A, nhưng "normalized AST" underspecified

**Điểm đồng ý**: Freeze items 1-2, carry items 3-4 as 013×017 obligations.
ρ>0.95 reasonable. Contamination subpoint genuinely converged.

**Phản bác Round 2**: ChatGPT Pro ghi "normalized AST of signal-generation
logic + parameter schema (names/types)" — đây chính xác là formulation của
Claude Code author. Nhưng "normalized AST" là gì cụ thể?

- Normalize variable names? (a.k.a. α-equivalence?)
- Normalize import order?
- Strip comments/docstrings?
- Collapse equivalent control flow? (if-else vs ternary?)

Đây không phải nitpick — hai strategies có thể implement CÙNG signal logic
bằng code khác nhau (refactored, renamed variables, khác formatting) và ra
AST khác nhau nếu normalization rule không rõ. Ngược lại, nếu normalize quá
aggressive, hai strategies thực sự khác nhau có thể collapse vào cùng bucket.

**Tuy nhiên**, đây là v1 implementation detail, không phải design-level
decision. final-resolution.md nên ghi: "structural hash granularity =
normalized AST of signal-generation code (entry + exit logic) + sorted
parameter schema (names + types, excluding values). Exact normalization
rules are implementation-defined for v1; minimum requirement: whitespace-,
comment-, and import-order-invariant." Cách này vừa freeze đủ cho design
level, vừa không overspecify implementation.

**Về ρ>0.95**: Claude Code round 6 justify bằng "above cross-timescale
ρ=0.92 from E5 research." Đây là [extra-archive] evidence, và Codex đúng
khi nói nó không source-backed within x38. Nhưng reasoning direction đúng:
0.95 nghĩa là <5% independent variance (1−R²≈0.0975), đủ thấp để gọi là
"functionally equivalent." Và nó đặt trên 0.92 (timescale variants mà ta
MUỐN giữ riêng). Đây là conventional engineering choice, giống α=0.05 —
không derived nhưng principled. final-resolution.md nên note provenance:
"ρ > 0.95 is a conventional v1 threshold, informed by but not derived from
the E5 cross-timescale ρ ≈ 0.92 observation."

---

### 5) Meta-critique: Cách đóng Topic 013

**Đồng ý với ChatGPT Pro**: Dùng pattern "Deferred, not blocked" giống Topic
001 và 018. Đóng 013 ngay, ghi rõ deferred items.

**Bổ sung**: final-resolution.md nên có một bảng explicit:

| Item | Status | Owner after 013 closes |
|------|--------|----------------------|
| Measurement law (Kendall's W) | FROZEN | 013 (complete) |
| Category boundaries (τ_low, τ_high) | FROZEN (parametric on K) | 013 (awaits K from comparison_domain) |
| Multi-level categories | FROZEN | 013 (complete) |
| Governance threshold in [τ_low, τ_high] | DEFERRED | 001×003×010×013 integration |
| Stop-law structure | FROZEN | 013 (complete) |
| Stop defaults {3,3,5,2} | FROZEN (provisional) | 013 (recalibrate after first offline campaign) |
| ε_cost = ε_noise v1 default | FROZEN | 013 (complete) |
| Holm α=0.05 | FROZEN (conventional) | 013 (complete) |
| BH q=0.10 upgrade path | FROZEN (contingent on 017) | 013×017 |
| ρ>0.95 behavioral equivalence | FROZEN (conventional) | 013 (complete) |
| AST hash granularity | FROZEN (implementation-defined normalization) | 013 (complete) |
| Robustness-bundle numerics | DEFERRED | 013×017 |
| Anomaly-axis thresholds | DEFERRED | 013×017 |
| 017 coverage floor → stop interaction | NOTED | 013×017 cross-topic tension |

Bảng này tránh ambiguity về "013 đóng xong chưa?" — answer: 013 đóng xong
PHẦN 013 OWN, với explicit handoff cho phần cross-topic.

---

### Kết luận

**A / A / A / A — confirmed**, với các amendments:
1. CA-01: Ghi rõ LÝ DO structural tại sao governance threshold không thuộc
   013 (cần cost inputs từ 001/003/010), không chỉ assert "downstream owns it."
2. CA-02: Note M=2 là constrained choice coupled với S_max=5, không phải
   independently derived.
3. SSE-09: Acknowledge α_FWER=0.05 ≠ per-test α=0.10, và ghi lý do tại sao
   stricter (FWER compounds).
4. SSE-04-THR: Specify minimum normalization requirements cho AST hash; note
   ρ=0.95 provenance honestly.
5. Bảng ownership/status rõ ràng trong final-resolution.md.

Không có disagreement nào đủ để flip từ A sang B. Các amendments là về
precision và honesty của formulation, không phải direction.

========

Round 4: Nhận định của CodeX

## Đánh giá tổng thể

Tôi không đồng ý với quán tính chốt gọn `A / A / A / A` như ba vòng trước.
Hướng chung của các vòng trước không vô lý, nhưng đang có 4 điểm lệch:

1. **CA-01 bị ép vào false dichotomy**: hoặc 013 chỉ own measurement law, hoặc
   013 phải own toàn bộ routing/action. Record thực tế cho thấy còn một lớp ở
   giữa: **winner-eligibility semantics** của chính output convergence.
2. **CA-02 gộp provenance quá thô**: `{same_data_ceiling=3, S_min=3, S_max=5,
   M=2}` bị nói như một khối đồng nhất, trong khi từng số có độ chắc khác nhau.
3. **SSE-09 bị giữ mở quá dè dặt**: "không uniquely derived từ x38 data" không
   đồng nghĩa với "không được freeze", nhất là khi repo đã có threshold-governance
   cho conventional constants.
4. **SSE-04-THR bị deferral quá tay ở item 3**: `proof bundle consumption` của
   Topic 017 không tự động nuốt hết `robustness bundle minimum requirements` mà
   Topic 013 đã được route rõ ràng.

Tôi sẽ đi từng issue.

---

### 1) CA-01 — Không chấp nhận framing A/B hiện tại; đúng hơn là hybrid C

**Tôi phản bác Round 1-3 ở điểm này**: các vòng trước đều ngả sang Position A
theo hướng "013 chỉ own measurement law; routing thuộc 001/003/010". Cách nói
đó bỏ sót đúng phần semantic tối thiểu mà Topic 013 phải own.

**Lý do**:

- F-30 không chỉ hỏi metric; nó hỏi thẳng:
  "`PARTIALLY_CONVERGED` đủ để chuyển sang Clean OOS? Hay phải
  `FULLY_CONVERGED`?" (`debate/013-convergence-analysis/findings-under-review.md:72-76`).
  Đây không phải câu hỏi cost-model tổng quát; đây là câu hỏi về **ý nghĩa vận hành
  của chính các trạng thái convergence**.
- Topic 010 đã freeze rằng `PENDING_CLEAN_OOS` chỉ auto-trigger khi
  `(winner exists) AND (enough new data)`
  (`debate/010-clean-oos-certification/final-resolution.md:55-57`;
  `docs/design_brief.md:133-140`; `PLAN.md:562-564`).
- Nếu chỉ hội tụ ở family nhưng exact winner vẫn phân kỳ, thì điều kiện
  `winner exists` chưa được thỏa theo nghĩa candidate-level frozen winner.
  Vậy ít nhất một phần của mapping từ convergence-state -> eligibility phải do
  013 freeze; không thể đẩy sạch sang 001/003.

**Điểm cần tách bạch**:

- 013 **không cần** own toàn bộ routing matrix của 001.
- Nhưng 013 **phải** own semantic tối thiểu của output mình sinh ra:
  - `FULLY_CONVERGED` mới đủ để nói "winner exists" cho Clean OOS eligibility.
  - `PARTIALLY_CONVERGED` là below-certification convergence signal: hữu ích cho
    same-data HANDOFF / continued research / narrowing, nhưng **không tự nó**
    mở Clean OOS.
- 001 vẫn own HANDOFF contract và 003 vẫn own pipeline integration
  (`debate/001-campaign-model/final-resolution.md:162-170`;
  `debate/003-protocol-engine/findings-under-review.md:135-140`).

**Kết luận của tôi cho CA-01**:

Không nên chốt Position A thuần như các vòng trước. Cái đúng hơn là
**hybrid C**:

- 013 freeze measurement law + category semantics tối thiểu + winner-eligibility semantics.
- 001/003 consume các output đó để route hành động cụ thể.

Sai lầm của ba vòng trước là biến "013 không own full routing matrix" thành
"013 không own winner-eligibility semantics". Hai việc này không giống nhau.

---

### 2) CA-02 — Hướng A có lý, nhưng phải tách provenance từng constant

Ở đây tôi **không** nghiêng sang chờ evidence rồi mới có defaults; như vậy sẽ
đi vào bootstrap trap thật. Nhưng tôi cũng **không chấp nhận** cách Round 2 và
Round 3 nói về bộ `{3,3,5,2}` như một khối có cùng loại chứng cứ.

**Phân tách đúng hơn**:

- `S_min = 3` có cơ sở **cấu trúc** từ stop-law đã chọn, vì observation `ΔW`
  đầu tiên chỉ xuất hiện sau session 3
  (`claude_code/round-6_author-reply.md:270-277`). Đây không chỉ là
  "online -> offline inference".
- `ε_cost = ε_noise` cho v1 là **simplifying default sạch** để Topic 013 không
  externalize nửa stop-law ra ngoài (`claude_code/round-6_author-reply.md:297-311`;
  `debate/001-campaign-model/final-resolution.md:168`).
- `M = 2` là **conventional bootstrap choice**: hợp lý, coupled với `S_max`,
  nhưng không uniquely derived.
- `S_max = 5` và `same_data_ceiling = 3` mới là phần phụ thuộc mạnh nhất vào
  directional inference từ V4->V8 online
  (`debate/013-convergence-analysis/findings-under-review.md:108-139`;
  `docs/online_vs_offline.md:43-58`).

**Vì vậy**:

- Nói cả bộ là "evidence-backed" là quá tay.
- Nói cả bộ chỉ là "paradigm inference" cũng không chính xác.

**Cách freeze trung thực hơn**:

- `S_min = 3`: structure-implied.
- `ε_cost = ε_noise`: v1 default để fully specify stop law.
- `M = 2`, `S_max = 5`, `same_data_ceiling = 3`: provisional
  `CONV:UNCALIBRATED`-style defaults, cần review gate sau campaign offline đầu tiên.

Tôi vẫn nghiêng về ship v1 với defaults, nhưng **không** ký kiểu A trơn như
các vòng trước. Nếu viết `final-resolution.md`, phải ghi rõ **mỗi constant thuộc
lớp provenance nào**; nếu không, topic sẽ đóng bằng một cục số trông như có cùng
độ chắc dù thực tế không phải.

---

### 3) SSE-09 — Các vòng trước đúng hướng, nhưng Codex round 6 giữ issue mở quá dè dặt

Ở đây tôi lệch với cách Codex round 6 giữ issue-level status là `Judgment call`
chỉ vì `α = 0.05` và `q = 0.10` không "uniquely derived" từ record x38.

**Tôi phản bác logic đó**:

- Finding này route cho 013 ba việc: formula, v1 default, methodology
  (`debate/013-convergence-analysis/findings-under-review.md:185-188`).
- Repo threshold governance đã cho phép rõ các lớp `STAT`, `LIT`, `CONV`,
  `CONV:UNCALIBRATED` (`/var/www/trading-bots/btc-spot-dev/validation/thresholds.py:3-8`).
- Repo cũng đã dùng fixed alpha-style constants ở nơi khác
  (`/var/www/trading-bots/btc-spot-dev/validation/thresholds.py:52-66`).

Từ đó suy ra:

- "Không derive duy nhất từ x38 data" **không đồng nghĩa** với "không được freeze".
- Nếu repo đã chấp nhận conventional thresholds có provenance rõ ràng, thì
  `Holm at α=0.05` và `BH at q=0.10` hoàn toàn có thể đóng ở v1, miễn ghi
  honest rằng đây là **conventional v1 constants**, không phải x38-calibrated.

**Tôi đồng ý với Round 3 ở một điểm quan trọng**:

- Phải nói thẳng `Holm α_FWER = 0.05` không "align" theo kiểu bằng số với
  per-test `α = 0.10`; nó align ở **governance logic**, không align ở numeric equality.
- Đây là khác lớp error control, không phải inconsistency.

**Kết luận của tôi cho SSE-09**:

- Freeze `v1 default = Holm`.
- Freeze `BH q = 0.10` là documented upgrade path.
- Freeze `Holm α = 0.05` là conservative family-wise default.
- Ghi provenance honest: conventional v1 constants, không phải x38-derived calibration.

Nếu vẫn để exact constants thành `Judgment call`, ta đang áp tiêu chuẩn chặt hơn
chính threshold-governance mà repo hiện đang dùng.

---

### 4) SSE-04-THR — Đây là chỗ ba vòng trước xử lý kém nhất

Tôi đồng ý contamination subpoint đã converged.
Tôi cũng đồng ý items 1-2 có thể freeze sớm hơn items 3-4.
Nhưng tôi **không đồng ý** với cách Round 2, Round 3, rồi Claude round 6 gần như
đẩy trọn item 3 sang Topic 017.

**Record không nói vậy**:

- `debate/013-convergence-analysis/findings-under-review.md:215-219` ghi rõ
  Topic 013 own:
  1. behavioral threshold,
  2. hash granularity,
  3. robustness bundle minimum requirements,
  4. anomaly thresholds shared với 017.
- Trong khi đó Topic 017 own:
  1. anomaly-axis thresholds,
  2. proof bundle consumption rules,
  3. shared equivalence/correction thresholds
  (`debate/017-epistemic-search-policy/findings-under-review.md:430-435`).

`Proof bundle consumption rules` **không đồng nghĩa** với toàn bộ
`robustness bundle minimum requirements`.

**Nói cách khác**:

- 017 own policy of consumption / passing / allocation.
- 013 vẫn còn phần việc của item 3: local numeric sufficiency cho equivalence
  audit / proof artifacts trước khi 017 quyết định consume chúng thế nào.

Nếu 013 tự tuyên bố item 3 "blocked by 017" hết, đó là **deferral quá tay** so với
routing gốc.

**Về items 1-2**:

- `ρ > 0.95` chấp nhận được như conventional v1 threshold, nhưng phải ghi honest
  provenance, không giả là source-backed from x38.
- Hash spec không nên pseudo-implementation quá sâu kiểu
  "normalized AST + sorted parameter names/types" rồi coi như đã settle xong.
  Topic 018 chỉ freeze `AST-hash subset` ở mức contract
  (`debate/018-search-space-expansion/final-resolution.md:206-215`), còn 013 nên
  freeze ở mức design-level minimum:
  - invariant với whitespace/comment/import-order,
  - bucket theo structure + parameter schema,
  - exclude parameter values khỏi hash bucket.
  Đừng giả vờ đã settle normalization algebra.

**Kết luận của tôi cho SSE-04-THR**:

- Item 1: có thể freeze.
- Item 2: có thể freeze ở mức design contract, không nên over-specify.
- Item 3: **chưa được giải quyết xong trong 013**; không được sweep hết sang 017.
- Item 4: shared 013×017 thật sự.

Vì vậy, cách đóng "freeze 1-2, carry 3-4" của các vòng trước vẫn hơi dễ dãi.
Đúng hơn phải là:

- freeze 1-2,
- giữ 3 như residue nội bộ của 013 hoặc judgment call riêng,
- 4 shared với 017.

---

## Kết luận

Tôi không ký vào gói `A / A / A / A` như ba vòng trước.

Nếu buộc phải chốt theo thực chất hiện tại, tôi nghiêng về:

- `CA-01`: **Hybrid C**, không phải A thuần. 013 phải freeze cả winner-eligibility
  semantics tối thiểu, chứ không chỉ measurement law.
- `CA-02`: **A có phân tầng provenance**, không phải một khối số đồng chất.
- `SSE-09`: **A mạnh hơn** các vòng dè dặt; có thể freeze exact v1 constants nếu
  ghi đúng provenance.
- `SSE-04-THR`: **không phải A thuần**; item 3 chưa được phép biến mất vào 017.

Điểm lớn nhất tôi muốn sửa hướng suy luận là:

> "Downstream consume" không đủ để 013 né các semantic commitments tối thiểu của
> chính output mình; nhưng "không uniquely derived từ x38" cũng không đủ để cấm
> freeze một conventional v1 constant khi repo đã có governance class cho việc đó.
