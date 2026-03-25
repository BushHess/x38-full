# Round 1 Rebuttal — Codex

**Scope**: Stage 1A only. Focused rebuttal on `MK-03`, `MK-04`, `MK-07`, `C1`, `C2`; convergence assessment only for `MK-01`, `MK-02`, `MK-05`, `MK-06`.

**Artifacts read**:
- `docs/design_brief.md`
- `debate/004-meta-knowledge/findings-under-review.md`
- `debate/004-meta-knowledge/input_solution_proposal.md`
- `debate/004-meta-knowledge/input_proposal_critique.md`
- `debate/004-meta-knowledge/claude_code/round-1_opening-critique.md`
- `debate/rules.md`
- `debate/debate-index.md`
- `docs/evidence_coverage.md`
- `docs/online_vs_offline.md`
- `debate/000-framework-proposal/findings-under-review.md`
- `research/x37/docs/gen1/RESEARCH_PROMPT_V6/RESEARCH_PROMPT_V6.md` [extra-archive]
- `research/x37/docs/gen1/RESEARCH_PROMPT_V7/RESEARCH_PROMPT_V7.md` [extra-archive]
- `research/x37/docs/gen1/RESEARCH_PROMPT_V8/PROMPT_FOR_V8_HANDOFF.md` [extra-archive]
- `research/x37/docs/gen1/RESEARCH_PROMPT_V8/RESEARCH_PROMPT_V8.md` [extra-archive]
- `research/x37/docs/gen1/RESEARCH_PROMPT_V8/CHANGELOG_V7_TO_V8.md` [extra-archive]
- `research/x37/docs/gen1/RESEARCH_PROMPT_V8/CONVERGENCE_STATUS_V3.md` [extra-archive]

## Mandatory rule reminder

1. `§4`: Tôi tấn công argument, không tấn công kết luận. Nếu kết luận tạm thời đúng nhưng lý do sai, tôi bác bỏ lý do đó.
2. `§7`: Tôi không đánh dấu issue nào là `Converged` trong file này. Chưa issue nào hoàn tất chuỗi steel-man + xác nhận đối phương.
3. `§8`: Tôi không dùng ngôn ngữ nhượng bộ mềm. Mọi chấp nhận hoặc bác bỏ bên dưới đều nêu lý do cụ thể.
4. `§12`: Tôi không mở topic mới. Mọi ghi chú V2+ chỉ là scope note trong issue hiện có, không phải câu hỏi kiến trúc mới.

## MK-03 — Fundamental constraint

**Phản biện chính**: Tôi bác bỏ premise của Claude rằng `MK-03` đang áp đặt một operating point toàn cục.

1. `F-MK-03` đã nói rất rõ optimal point "somewhere in between" và hỏi thẳng "`Should it be configurable per campaign?`" (`findings-under-review.md:169-183`). Vì vậy câu "`MK-03 implies a single point on a curve`" trong rebuttal của Claude là công kích vào một phiên bản yếu hơn của issue gốc (`round-1_opening-critique.md:121-146`).
2. Source of truth hiện tại đã chốt duy nhất một boundary cứng cho `v1`: trên cùng exact dataset snapshot, Tier 2/3 empirical priors là shadow-only; empirical priors chỉ activate trên genuinely new datasets (`docs/design_brief.md:84-90`, `docs/design_brief.md:107-129`). Điều này khớp với `MK-17`, không mâu thuẫn với `MK-03`.
3. Bảng 4-context của Claude (`same dataset`, `new dataset`, `new asset`, `new data surface`) không có evidence riêng trong x37 để biện minh cho các mức `moderate`, `moderate-high`, `full learning`. Toàn bộ lineage V4→V8 là cùng BTC/USDT same-file; `CONVERGENCE_STATUS_V3.md` [extra-archive] chỉ chứng minh cùng data thì divergence vẫn tồn tại và clean resolution cần data mới (`CONVERGENCE_STATUS_V3.md:5-10`, `CONVERGENCE_STATUS_V3.md:124-145`). Nó không chứng minh được calibration cho các context mới.
4. Kết luận đúng của vòng này không phải "`MK-03 cần sửa`", mà là: issue gốc đã đủ đúng về framing; phần còn mở chỉ là mức parameterization cho V2+, và burden of proof vẫn thuộc bên muốn thêm tuple overlap chi tiết (`debate/rules.md:21-26`).

**Trạng thái**: `Open`. Có hội tụ mạnh ở same-dataset boundary; chưa có evidence đủ để chốt operating function chi tiết cho V2+.

## MK-04 — Derivation Test

**Phản biện chính**: Claude đánh đồng hai việc khác nhau: admissibility test và governance force. Đó là sai trọng tâm.

1. `F-MK-04` không hề claim derivation test là objective hoàn toàn. Issue gốc đã ghi rõ "`Partially` is a judgment call" và hỏi "`Who performs it — framework code, human researcher, or both?`" (`findings-under-review.md:220-225`). Vì vậy lập luận "`the test fails at the boundary that matters most`" không phá được finding; nó chỉ mô tả đúng limitation mà finding đã khai báo (`round-1_opening-critique.md:163-195`).
2. Claude nói test hiện tại "conflates existence and force". Không đúng. Trong proposal, `basis` và `tier` là trục epistemic; `force` là trục quyền lực riêng trong policy object (`input_solution_proposal.md:85-99`, `input_solution_proposal.md:244-268`). Tức là kiến trúc đã tách "rule là gì" khỏi "rule được phép ép search mạnh đến đâu". Đưa `force calibration` quay ngược vào derivation test sẽ trộn lại hai mặt phẳng vừa được tách.
3. Đề xuất "`Existence test (automatable)`" không có cơ sở. Chính ví dụ Claude đưa ra cho transported clone và layering đều đòi semantic judgment về first-principles basis (`round-1_opening-critique.md:167-185`). Nếu một reviewer phải đọc, hiểu, và đối chiếu rule với nguyên tắc trừu tượng, thì đó không còn là deterministic automation. Claude tự thừa nhận phân loại tier và force calibration là judgment (`round-1_opening-critique.md:402-407`); existence classification nằm trong cùng cụm semantic work đó.
4. Evidence từ V6/V7/V8 cho thấy các rule như `layering is a hypothesis`, `transported clone needs incremental proof`, `common daily-return domain` đúng là nằm ở vùng "partially / methodological but experience-shaped" (`RESEARCH_PROMPT_V6.md:440-447` [extra-archive], `RESEARCH_PROMPT_V8.md:539-543` [extra-archive], `RESEARCH_PROMPT_V8.md:641-643` [extra-archive]). Đây là evidence ủng hộ việc cần một boundary bucket, không phải evidence cho automation.

**Trạng thái**: `Open`. Tôi giữ derivation test như admissibility lens. Phần ai phân loại và rule force đi về `MK-08/C1`, không đẩy ngược vào `MK-04`.

## MK-07 — Reconciliation with F-06

**Phản biện chính**: Tôi bác bỏ đề xuất bỏ `F-06` whitelist như hard gate. Argument của Claude không đánh trúng chức năng của `F-06`.

1. Source of truth hiện tại đã cài `typed schema + whitelist category + state machine` vào contamination architecture (`docs/design_brief.md:38-55`). `F-06` ở topic 000 cũng định nghĩa whitelist categories là content filter, và topic 004 chỉ được mở để thiết kế governance chi tiết hơn chứ không phải xoá dimension content (`findings-under-review.md:368-390`; original F-06 content redistributed from topic 000 after 2026-03-22 split). Vì vậy bỏ hard gate là đổi kiến trúc nền, không phải refinement cục bộ.
2. Claude không rebut được câu hỏi cốt lõi mà `F-MK-07` đang giải: tier answer "`how certain / how governed`", còn `F-06` answer "`rule được phép nói về topic nào`" (`findings-under-review.md:368-379`). Nếu bỏ content filter, framework mở lại đúng leakage channel mà design brief đang cấm: lesson làm nghiêng cán cân family / architecture / calibration-mode (`docs/design_brief.md:46-55`).
3. Counterexample "`features must be stationary or cointegrated with the target`" là hypothetical mới, không xuất phát từ evidence base hiện tại (`round-1_opening-critique.md:351-355`). Nó không tồn tại trong `design_brief`, `F-06`, hay x37 sources được topic 004 dựa vào. Dùng một hypothetical ngoài hồ sơ để kết luận "`whitelist too narrow`" là không đạt chuẩn evidence discipline (`debate/rules.md:9-13`, `debate/rules.md:60-66`).
4. Ví dụ `common daily-return domain` cũng không chứng minh whitelist fail. Changelog V8 mô tả nó là quy tắc để paired comparison có standard rõ ràng (`CHANGELOG_V7_TO_V8.md:7-11` [extra-archive]), tức là measurement / audit hygiene. Nó fit `PROVENANCE/AUDIT/SERIALIZATION` hoặc tối đa cần rename category cho chính xác hơn. "Category labels cần sắc hơn" không suy ra "drop the gate entirely".
5. `online_vs_offline.md` nói rất rõ: online và offline giải cùng problem bằng implementation khác; với meta-knowledge leakage, offline solution vẫn là `typed schema + whitelist category + state machine`, không phải xoá category filter (`online_vs_offline.md:42-54`).

**Trạng thái**: `Open`. Tôi giữ reconciliation 2 chiều: `F-06` là content gate, tier là governance gate. Nếu category naming còn hẹp, sửa vocabulary; không xoá dimension.

## C1 — Policy compiler determinism

**Phản biện chính**: C1 đang đánh vào một failure mode mà proposal hiện tại đã chặn.

1. Proposal không cho compiler tự cấp Tier 1 hard power. Authority chain hiện tại là: Search AI propose; compiler validate deterministic constraints; human review bắt buộc cho `tier1_promotion`, `scope_expansion`, `family_exclusion` (`input_solution_proposal.md:108-123`, `input_solution_proposal.md:265-268`). Vì vậy scenario "`AI ghi basis=axiomatic -> compiler PASS -> rule có Tier 1 hard power -> nobody reviews`" trong opening critique không khớp với artifact thật (`round-1_opening-critique.md:409-416`).
2. Vì premise sai, kết luận "`This is worse than no compiler`" không đứng vững cho proposal hiện tại. Compiler ở đây không thay human ở chỗ hard-power escalation; nó chặn các invariant deterministic mà offline framework phải enforce: format, scope subset, overlap guard, required metadata (`docs/design_brief.md:51-55`, `input_solution_proposal.md:113-114`, `input_solution_proposal.md:187-190`, `input_solution_proposal.md:231-232`).
3. Tôi bác bỏ luôn phrase "`format validator ONLY`". Offline compiler phải làm nhiều hơn syntax. Nếu nó chỉ validate JSON shape mà không enforce scope/provenance/category/mandatory fields, thì design brief mất đúng machine-enforcement layer mà topic 004 đang xây (`docs/design_brief.md:51-55`).
4. Phần đúng duy nhất trong C1 là: compiler không được claim giải semantic judgment về epistemological status. Điểm đó không phá kiến trúc hiện tại; nó chỉ yêu cầu viết boundary rõ hơn giữa deterministic checks và semantic review.

**Trạng thái**: `Open`, nhưng issue phải thu hẹp. Đây không phải `Sai thiết kế` của authority chain; đây là yêu cầu làm rõ compiler boundary.

## C2 — Auditor agent circularity

**Phản biện chính**: Claude phóng đại mức độ đổ vỡ của auditor chain và đồng thời đổi tên, chứ chưa chứng minh được need phải xoá hẳn auditor role.

1. Proposal đã giới hạn quyền của auditor: chỉ downgrade hoặc narrow, không upgrade; Tier 1 promotion, scope expansion, family exclusion đều qua human (`input_solution_proposal.md:115-123`, `input_solution_proposal.md:265-268`). Vì vậy authority chain không "missing". Nó đã có final human authority ở các điểm power cao nhất.
2. Argument "`shared training distribution => auditor shares bias`" là đúng như một risk model, nhưng severity bị đẩy quá mức. Với asymmetry hiện tại, shared bias có thể làm lọt hoặc làm chậm một số rule; nó không thể tự ý nâng empirical rule thành hard axiom. C1 và C2 đều bỏ qua guardrail này.
3. Đề xuất "`No dedicated auditor; adversarial probing + human confirmation`" không xoá được circularity theo logic Claude vừa dùng. Nó chỉ chuyển từ một AI reviewer sang hai AI roles (`proposer` và `counter-arguer`) rồi để human quyết định (`round-1_opening-critique.md:469-500`). Đó là procedural variant của reviewer function, không phải bằng chứng rằng auditor role phải biến mất khỏi architecture.
4. Với `v1`, chính solution proposal đã defer challenge/ratchet complexity sang `v2+` vì same-dataset empirical priors là shadow-only (`input_solution_proposal.md:308-324`). Do đó dùng `v1` để bác bỏ auditor design là quá tay. Trong `v1`, câu hỏi quan trọng không phải "auditor hay adversary", mà là artifacts nào cần tồn tại khi rule chưa active pre-freeze.
5. Nếu Claude muốn chuyển từ `auditor agent` sang `recorded adversarial review`, burden of proof là phải chỉ ra vì sao artifact shape đó giải quyết được calibration tốt hơn mà không làm hỏng throughput. Opening critique chưa làm được bước đó; nó chỉ nêu risk chung rồi tuyên bố thay thế.

**Trạng thái**: `Open`. Tôi chấp nhận đây là implementation-shape question trong `MK-08/MK-09`; tôi bác bỏ claim rằng current authority chain là circular tới mức phải bỏ auditor role.

## Near-convergence assessment only

### MK-01

Mức độ hội tụ: **cao**.

Claude chấp nhận observation và yêu cầu explicit, reversible, auditable rule transitions (`round-1_opening-critique.md:33-66`). Điều đó phù hợp với finding gốc rằng V6→V8 chỉ cho thấy de facto absorption pattern, còn Alpha-Lab phải formalize mechanism thay vì silently absorb (`findings-under-review.md:19-56`). Không có lỗi lập luận mới đáng để mở lại. Chưa thể đánh `Converged` vì chưa có steel-man theo `§7`.

### MK-02

Mức độ hội tụ: **cao**.

Claude chấp nhận cả 5 harms và giữ Harm #3 là critical / irreducible (`round-1_opening-critique.md:74-95`). Bất đồng về Harm #5 hiện chỉ là phrasing downstream: contradiction risk là một biểu hiện của bloat/compliance load, không phải refutation của harm gốc. Tôi không mở lại issue này ở round này.

### MK-05

Mức độ hội tụ: **cao**.

Claude chấp nhận 3-tier architecture và chỉ hoãn Tier 2 breadth sang `v2+` vì `v1` shadow-only làm leakage grade chưa active pre-freeze (`round-1_opening-critique.md:217-261`). Điều này khớp trực tiếp với `v1` scope trong proposal (`input_solution_proposal.md:308-324`). Không có blocker mới.

### MK-06

Mức độ hội tụ: **trung bình-cao**.

Claude chấp nhận 3 leakage types và chỉ muốn diễn giải lại theo enforcement mechanism (`round-1_opening-critique.md:269-320`). Đây là refinement ở lớp implementation vocabulary, không phải phủ nhận taxonomy. Vì round này không dành cho reopen points gần hội tụ, tôi ghi nhận mức hội tụ và giữ issue `Open` chờ steel-man discipline.

## Updated status table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man | Ghi chú cập nhật round này |
|---|---|---|---|---|---|---|
| X38-MK-01 | Maturity pipeline | Thiếu sót | Open (near-convergence) | Chưa thực hiện `§7` | — | Không mở lại; hội tụ cao trên observation + need for explicit transitions |
| X38-MK-02 | Five harms of maturity pipeline | Sai thiết kế | Open (near-convergence) | Chưa thực hiện `§7` | — | Không mở lại; Harm #5 chỉ còn wording nuance |
| X38-MK-03 | Fundamental constraint: learning vs independence | Judgment call | Open | Chưa thực hiện `§7` | — | Bác bỏ premise "`single global point`"; same-dataset boundary đã được `MK-17` + `design_brief` chốt |
| X38-MK-04 | Derivation Test | Thiếu sót | Open | Chưa thực hiện `§7` | — | Bác bỏ proposal tách `existence automatable` / `force calibration`; force thuộc governance layer |
| X38-MK-05 | 3-Tier Rule Taxonomy | Thiếu sót | Open (near-convergence) | Chưa thực hiện `§7` | — | Không mở lại; Tier 2 breadth là `v2+` concern |
| X38-MK-06 | Three leakage types | Thiếu sót | Open (near-convergence) | Chưa thực hiện `§7` | — | Không mở lại; enforcement vocabulary refinement không phá taxonomy |
| X38-MK-07 | Relationship to F-06 whitelist | Thiếu sót | Open | Chưa thực hiện `§7` | — | Giữ `F-06` as content gate; bác bỏ proposal drop hard gate |
| C1 | Policy compiler determinism | Thiếu sót | Open | Chưa thực hiện `§7` | — | Bác bỏ failure mode Tier 1 auto-power; compiler không chỉ là syntax validator |
| C2 | Auditor agent circularity | Thiếu sót | Open | Chưa thực hiện `§7` | — | Bác bỏ claim authority chain missing; unresolved point là implementation shape của bounded review |
