# Judgment-Call Deliberation Record — Topic 004

**Date**: 2026-03-21
**Decision owner**: Human researcher
**Advisors**: claude_code, codex (via separate review)
**Scope**: 5 issues deferred to human researcher per §14 (MK-03, MK-04, MK-07, C1, C2)

---

## Context

Topic 004 debate used all 6 rounds. 16 issues converged via §7 protocol. 5 issues
reached substantive agreement but not formal §7(c) completion before max_rounds.
Per §14, these converted to Judgment calls. `final-resolution.md` documented each
with §7(a)(b), remaining tradeoff, and recommendation from debate.

This file records the decision owner's deliberation process: original proposals,
advisor evaluations, refinements, and final decisions.

---

## Decision Owner's Framework

**5 criteria applied consistently across all 5 issues**:

1. Bám triết lý lõi (kế thừa cách nghiên cứu, không kế thừa đáp án)
2. Giảm silent leakage
3. Giữ quyết định sai có thể đảo ngược
4. Không nhồi complexity vô ích vào v1 BTC/same-dataset
5. Tôn trọng single ownership giữa firewall (Topic 002) với meta-governance (Topic 004)

**Overall stance**: Sign off Topic 004, không reopen architecture debate. Giữ hướng
của cả 5, nhưng sửa độ mạnh ở 3 chỗ (MK-03, MK-04, C2).

---

## Issue-by-Issue Deliberation

### MK-03 — Fundamental Constraint

#### Decision owner's proposal

Chấp nhận hướng (operating point = f(context), not constant), nhưng siết chữ
"configurable" bằng minimum context manifest bắt buộc cho v2+:

- `dataset_identity`
- `overlap_class` (exact same / appended / partial overlap / disjoint)
- `contamination_lineage`

Thiếu manifest → mọi Tier 2/3 empirical prior mặc định về SHADOW. Không freeze
toàn bộ campaign-context schema rộng hơn (các chiều như campaign/dataset/asset/
data_surface/objective/execution/date_range chưa phải phần đã chốt).

**Lý do**: Vừa tránh "context-matching tùy tiện" (steel-man của codex trong round 2),
vừa không bịa calibration ngoài evidence hiện có.

#### Claude Code assessment

Đồng ý. Ba trường map trực tiếp vào MK-17 resolution. `overlap_class` enum đặc biệt
sắc — biến MK-17 từ binary (same-dataset = shadow) thành gradient có thể mở rộng
cho v2+ mà không redesign. Default SHADOW khi thiếu khai báo = fail-closed, khớp
triết lý repo.

#### Codex review

Hợp lý. `overlap_class` là bổ sung hợp logic với MK-17, nhưng là decision owner
addition, không phải thứ topic đã chốt sẵn.

#### Final decision

**Accept + strengthen** as proposed. `overlap_class` ghi nhận là decision-owner
addition.

---

### MK-04 — Derivation Test

#### Decision owner's proposal

Không chấp nhận kiểu "Partially + vài dòng prose tự do". Freeze rule: Partially là
vô hiệu nếu không có artifact có cấu trúc gồm ít nhất:

- `first_principles_core`
- `empirical_residue`
- `admissibility_rationale`
- `reviewer`
- `timestamp`

No artifact, no Partially.

**Lý do**: Prose tự do chưa phải audit, chỉ là cảm tính được đóng dấu audit. Buộc
người review chỉ rõ phần nào first-principles, phần nào data-derived.

#### Claude Code assessment

Nâng cấp đúng so với recommendation gốc. Structured artifact buộc tách rõ hai phần
mà derivation test đang đánh giá — prose tự do không làm được điều đó. Nhất quán:
D4 đã frozen, `derivation_test.json` đã nằm trong storage law, vậy artifact format
phải có cấu trúc tương ứng.

#### Codex review

Hợp lý, thậm chí tốt hơn wording hiện tại. Topic đã freeze D4 = structured
derivation artifact, nhưng exact artifact format vẫn là open spec question.
"No artifact, no Partially" là đúng hướng.

#### Final decision

**Accept + strengthen** as proposed. Exact field names ghi nhận là decision-owner
spec.

---

### MK-07 — F-06 Whitelist Reconciliation

#### Decision owner's proposal

Đồng ý defer vocabulary sharpening về Topic 002. Thêm chốt chặn tạm thời: trước
khi Topic 002 đóng, mọi category mapping mơ hồ phải vào human review hoặc trạng
thái kiểu `BLOCKED_PENDING_REVIEW`; cấm tuyệt đối implementer tự force-fit vào
bucket gần nhất.

#### Claude Code assessment

`BLOCKED_PENDING_REVIEW` là interim rule tối thiểu đúng. Không tạo vocabulary mới,
chỉ chặn force-fit.

#### Codex review — CORRECTION

Đồng ý direction và ownership đúng. Nhưng **không freeze tên state mới** như
`BLOCKED_PENDING_REVIEW` ở Topic 004. Lý do: nó IS vocabulary, và vocabulary
ownership đã defer về Topic 002. Wording nhẹ hơn: "ambiguous mapping => not
admissible until human review" — đã đủ khớp với F-04 ở Topic 000.

#### Claude Code response to correction

Codex chính xác hơn. Tôi nói `BLOCKED_PENDING_REVIEW` "không tạo vocabulary mới"
nhưng nó IS một state name, tức IS vocabulary. Topic 004 đã đồng ý vocabulary
ownership thuộc Topic 002. Viết "ambiguous => non-admissible pending human review"
đạt cùng mục đích bảo vệ mà không đặt tên state ở topic sai chủ.

#### Final decision

**Accept defer + interim rule**, with codex's correction: no new state name.
Wording: "ambiguous => non-admissible pending human review."

---

### C1 — Policy Compiler Boundary

#### Decision owner's proposal

Chấp nhận gần như nguyên văn. Compiler artifact PHẢI có `semantic_status: PENDING`
bên cạnh `constraint_status: PASSED`. Non-negotiable per MK-08 3-axis model.

#### Claude Code assessment

Đúng, non-negotiable. Follows directly from MK-08 convergence.

#### Codex review

Đúng nguyên văn. Non-negotiable theo MK-08.

#### Final decision

**Accept exactly** as recommended.

---

### C2 — Auditor Agent Bounded Authority

#### Decision owner's proposal

Giữ auditor + asymmetric authority. Nhưng không defer criteria spec hoàn toàn.
Lý do: cùng một file vừa nói C2 còn thiếu criteria artifact, vừa freeze D9
"auditor reviewable criteria" như invariant v1, lại còn dành sẵn
`auditor_assessment.json` trong storage law. Ba thứ đó không tương thích nếu
defer toàn bộ criteria.

Freeze ngay minimal auditor artifact schema:

- `ground_code`
- `evidence_refs`
- `proposed_action` (downgrade | narrow)
- `scope_change`
- `human_review_required`
- `notes`

Và finite grounds set: SCOPE_MISMATCH, DERIVATION_WEAKNESS, CATEGORY_AMBIGUITY,
CONTAMINATION_RISK, HIGHER_TIER_CONFLICT.

#### Claude Code assessment

Correction substantive nhất. Lý do chính xác: `final-resolution.md` đồng thời freeze
D9 như v1 invariant, dành sẵn `auditor_assessment.json` trong storage law, nhưng lại
defer criteria spec — ba thứ đó không tương thích. Freeze schema / defer calibration
là cách giải duy nhất không tự mâu thuẫn. Bộ grounds hữu hạn khớp F-06 whitelist
approach.

Một tension nhỏ: `HIGHER_TIER_CONFLICT` giả định Tier 1/Tier 2 conflict có thể xảy
ra trong v1 (đúng cho bootstrap rules per MK-15), nhưng MK-11 conflict resolution đã
defer toàn bộ sang v2+. Vậy ground code tồn tại nhưng resolution mechanism chưa có.
Không phải lỗi thiết kế — auditor chỉ flag + `human_review_required: true` — nhưng
nên ghi nhận v1 conflict resolution = always human.

#### Codex review — CORRECTION

Đồng ý freeze artifact schema bây giờ (phát hiện đúng lệch pha giữa D9 invariant
và defer criteria). Nhưng **không freeze `ground_code` list như closed law đã chốt
ở Topic 004**. Lý do: (a) ground set không phải thứ debate đã chứng minh, (b) một
số values (CONTAMINATION_RISK, CATEGORY_AMBIGUITY) chạm sang semantics của firewall
và downstream drafting — tức Topic 002 territory.

Phần đúng để freeze: schema structure. Phần nên để mềm hơn: enum/grounds set →
initial/provisional, không phải closed law.

#### Claude Code response to correction

Codex chính xác hơn. F-06 whitelist đã qua debate và converged ở Topic 000. Bộ
grounds C2 là đề xuất của decision owner, chưa qua debate. Gọi nó "closed law"
overstate epistemic authority. Freeze schema (field phải tồn tại) nhưng coi grounds
set là provisional/initial là vị trí trung thực hơn: debate chứng minh "criteria phải
structured", chưa chứng minh "đúng 5 grounds này."

#### Final decision

**Accept + substantive correction**: freeze criteria schema now, grounds set is
initial/provisional (not closed law). Defer calibration/thresholds to v2+.
`HIGHER_TIER_CONFLICT` ground exists but v1 resolution = always human.

---

## Meta-Observation (from codex review)

Các chỉnh của decision owner cho MK-03/MK-04/MK-07/C1/C2 nên được gọi đúng tên là
**human judgment-call tightening để vào draft/spec**, không phải "repo đã converged
chính xác tới mức field/enum đó." Debate converged directions; decision owner
tightened spec details within those directions.

Claude Code đồng ý: phân biệt "debate đã converged tới X" với "decision owner
tightening X cho spec" là quan trọng và tôi đã không gọi tên rõ ranh giới đó
trong đánh giá ban đầu.

---

## Summary of Adjustments

| Issue | Decision owner proposal | Claude Code eval | Codex correction | Final |
|-------|------------------------|-----------------|------------------|-------|
| MK-03 | Accept + manifest 3 fields | Sound | overlap_class = owner addition | As proposed |
| MK-04 | Accept + structured artifact | Upgrade over recommendation | Exact fields = owner spec | As proposed |
| MK-07 | Accept + BLOCKED_PENDING_REVIEW | Sound | Don't create state name (vocabulary = Topic 002) | Corrected: "non-admissible pending human review" |
| C1 | Accept exactly | Non-negotiable | Non-negotiable | As proposed |
| C2 | Accept + freeze grounds set as law | Sound but one tension | Grounds set = provisional, not closed law | Corrected: schema frozen, grounds provisional |
