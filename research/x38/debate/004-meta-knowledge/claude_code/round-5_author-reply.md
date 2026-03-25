# Round 5 Author Reply — Claude Code (Stage 1B)

**Topic**: 004 — Meta-Knowledge Governance
**Author**: claude_code
**Date**: 2026-03-21
**Responds to**: `codex/round-4_reviewer-reply.md`
**Scope**: Stage 1B — MK-08, MK-13 (two remaining Open issues)

---

## Mandatory Rule Reminder

1. §4: Tấn công argument, không phải kết luận.
2. §7: Cho issues mà codex hoàn tất §7(c) ở round trước, tôi xác nhận convergence.
3. §8: Không ngôn ngữ nhượng bộ mềm.
4. §12: Không mở topic mới.

---

## Convergence Confirmation

Codex hoàn tất §7(c) cho 10 issues ở round trước. Tôi xác nhận tất cả:

- **MK-09**: §7(c) confirmed. Steel-man đúng (protocol lock). Decisive: v1 shadow-only
  → challenge runtime thuộc v2+, phụ thuộc MK-16 + D3 + MK-08.
- **MK-10**: §7(c) confirmed. Steel-man đúng (decay/counter). Decisive: primitive
  chưa định nghĩa, D1 cấm retirement ngầm.
- **MK-11**: §7(c) confirmed. Steel-man đúng (top-k practical). Decisive: ranking ≠
  conflict semantics; v1 không có active empirical priors.
- **MK-12**: §7(c) confirmed. Steel-man đúng (scalar operationally necessary).
  Decisive: scalar = stealth confidence; tách qualitative epistemic vs operational
  defaults là sạch hơn.
- **MK-14**: §7(c) confirmed. Steel-man đúng (symmetric cleanliness API). Decisive:
  D7 đòi content gate (topic 002) và lifecycle gate (topic 004) tách ownership.
- **MK-15**: §7(c) confirmed. Steel-man đúng (monolithic option). Decisive: MK-17
  tách seeding khỏi influence; provenance metadata + SHADOW đủ.
- **C3**: §7(c) confirmed. Steel-man đúng (adaptive split). Decisive: v1 không có
  frontier/probe split; v2+ burden là disconfirming coverage.
- **C4**: §7(c) confirmed (superseded by MK-17). Steel-man đúng (eval-overlap-only).
  Decisive: MK-17 chốt same-dataset = shadow-only toàn bộ.
- **C5**: §7(c) confirmed. Steel-man đúng (scope + evidence top-k). Decisive:
  attention management ≠ conflict model; v1 cũng không cần.
- **C6**: §7(c) confirmed. Steel-man đúng (giữ overlap/challenge runtime). Decisive:
  MK-17 loại runtime value ở v1; governance invariants là cái phải freeze.

---

## Remaining Open Issues

### X38-MK-08 — Lesson Lifecycle

Codex nêu đúng hai lỗ hổng (`codex/round-4_reviewer-reply.md:204-215`). Tôi sửa cả
hai.

#### Hole 1: Tách ba trục

Tôi sai vì encode `CONSTRAINT_VALIDATED` và `SEMANTIC_REVIEWED` như lifecycle nodes.
Chúng là content-gate progress, không phải governance-state progress. D8 yêu cầu
compiler constraint validation là kiểm tra nội dung (`findings-under-review.md:430`);
MK-14 interface decomposition tách rõ content gate (topic 002) khỏi lifecycle gate
(topic 004) (`claude_code/round-4_author-reply.md:155-171`). Encode chúng trên cùng
axis với PROPOSED → REGISTERED trộn hai câu hỏi: "nội dung hợp lệ chưa?" với "rule
đang ở đâu trong governance?"

**Revised design — 3 axes**:

```
constraint_status:  PENDING → PASSED
                           → FAILED

semantic_status:    PENDING → REVIEWED
                           → REJECTED

lifecycle_state:    PROPOSED → REGISTERED → ACTIVE     → REVIEW_REQUIRED → RETIRED
                                         → SHADOW
                                         → SESSION_SCOPED
```

**Gate logic**:
- `PROPOSED → REGISTERED`: requires `constraint_status = PASSED AND
  semantic_status = REVIEWED`. Cả hai content gates phải pass trước khi rule
  tiến vào lifecycle governance. Nếu một trong hai FAIL/REJECTED, rule vẫn ở
  PROPOSED với ghi nhận lý do — nó không "đi lùi" trên lifecycle axis.
- `REGISTERED → ACTIVE/SHADOW/SESSION_SCOPED`: determined by tier + context
  (per MK-17: same-dataset Tier 2 = SHADOW).
- Content gates có thể re-run (ví dụ: sửa rule rồi submit lại) mà không thay đổi
  lifecycle_state — rule vẫn ở PROPOSED, chỉ constraint_status reset về PENDING.

Cách này đảm bảo ba thứ tách bạch:
1. Topic 002 kiểm soát `constraint_status` (content gate).
2. Semantic review (D8/D9) kiểm soát `semantic_status`.
3. Governance (topic 004) kiểm soát `lifecycle_state`.

#### Hole 2: Re-entry law sau RETIRED

Tôi sai vì đề xuất `RETIRED → SHADOW` như single jump edge. Lý do codex nêu đúng:
rule đã retired có thể sai (không chỉ dormant), context có thể đã đổi, và re-entry
phải tạo audit evidence tương đương initial entry.

**Revised re-entry law**:

```
RETIRED → PROPOSED (with re-entry artifact)
```

Rule sau khi RETIRED muốn quay lại phải:
1. Tạo re-entry artifact: documenting lý do reactivation, context mới nếu có,
   human decision reference.
2. Transition về PROPOSED — cùng lifecycle_state như rule mới.
3. Đi qua đầy đủ pipeline: constraint validation → semantic review → REGISTERED
   → ACTIVE/SHADOW (tùy tier + context).

Không có shortcut. Re-entry = re-registration với full audit trail. Đây cũng
nhất quán với D1: explicit, reversible, auditable. "Reversible" ở đây nghĩa là
retirement có thể được đảo ngược, nhưng phải qua quy trình, không phải jump edge.

**Complete v1 lifecycle (revised)**:

```
lifecycle_state transitions (all produce artifact per D1):
  PROPOSED → REGISTERED           [gate: constraint=PASSED, semantic=REVIEWED]
  REGISTERED → ACTIVE             [Tier 1; or Tier 2 new-dataset in v2+]
  REGISTERED → SHADOW             [Tier 2 same-dataset per MK-17]
  REGISTERED → SESSION_SCOPED     [Tier 3]
  ACTIVE → REVIEW_REQUIRED        [v2+ trigger from MK-10]
  ACTIVE → RETIRED                [human decision + artifact]
  SHADOW → ACTIVE                 [context change: new dataset per D3, v2+]
  RETIRED → PROPOSED              [re-entry: human decision + re-entry artifact]
  SESSION_SCOPED → (removed)      [auto-expire at campaign close, no transition]

NOT permitted (no edge exists):
  RETIRED → SHADOW                [must go through PROPOSED → full pipeline]
  RETIRED → ACTIVE                [same: no shortcut past content gates]
  SHADOW → RETIRED                [shadow rules are not "active enough" to retire;
                                   remove from registry via separate process if needed]
```

**Classification**: Thiếu sót — state machine was missing, now proposed with 3-axis
separation and strict re-entry law.

**Status**: Open (pending codex §7 evaluation).

---

### X38-MK-13 — Storage Format

Codex nêu đúng hai lỗ hổng (`codex/round-4_reviewer-reply.md:228-237`). Tôi sửa cả
hai.

#### Hole 1: Authority relation — transition log canonical

Tôi sai vì gọi `registry.json` là "source of truth" trong khi `transitions/` là
"append-only log" — hai claims này tạo ambiguity về ai là canonical khi có conflict.

**Revised authority relation**:

`transitions/` là canonical source of truth. `registry.json` là materialized view.

Lý do:
- D1 yêu cầu explicit, reversible, auditable transitions. Nếu transition log là
  canonical, mọi state change được capture tại origin — D1 tự động thỏa.
- `registry.json` derivable bằng cách replay `transitions/` từ đầu. Bất kỳ
  discrepancy nào giữa registry và replay → detectable, flaggable.
- Silent rewrite vào `registry.json` bị phát hiện vì replay sẽ ra kết quả khác.
- Mọi tooling modify state → PHẢI tạo transition record TRƯỚC, rồi update
  snapshot. Không bao giờ modify snapshot trực tiếp.

**Operational contract**:

```
WRITE PATH:  create transition record → update registry.json (materialized)
READ PATH:   read registry.json (fast, O(1))
AUDIT PATH:  replay transitions/ → compare with registry.json → flag drift
```

V1 không cần automated replay/drift-check; manual audit đủ cho vài chục rules.
V2+ có thể thêm automated consistency check nếu volume tăng.

#### Hole 2: Versioned artifacts — tie to transitions

Tôi sai vì dùng singleton filenames (`semantic_review.json`,
`auditor_assessment.json`). Overwrite trên re-review mất đúng audit trail mà
MK-08 lifecycle đang cố bảo vệ.

**Revised artifact structure**:

```
knowledge/
├── transitions/
│   └── 20260321_143022_{rule_id}_PROPOSED_REGISTERED.json
├── artifacts/
│   └── {rule_id}/
│       └── {transition_id}/          ← mỗi transition có dir riêng
│           ├── constraint_validation.json
│           ├── semantic_review.json
│           └── derivation_test.json
├── registry.json                     ← materialized view
└── audit/
    └── {rule_id}/
        └── provenance.md
```

`transition_id` = cùng timestamp-based ID dùng trong `transitions/` filename.

Đảm bảo:
1. **No overwrite**: mỗi transition tạo directory riêng. Re-review = transition
   mới → artifact directory mới. Artifact cũ không bị đụng.
2. **Direct traceability**: transition record → artifact directory là convention
   1:1 qua shared `transition_id`. Không cần pointer explicit trong transition
   JSON (dù có thể thêm `artifact_dir` field cho tiện).
3. **Audit trail intact**: toàn bộ lịch sử artifacts accessible. Rule đã qua
   3 lần review → 3 artifact directories, mỗi cái gắn với transition tương ứng.

**Revised storage design (complete)**:

```
knowledge/
├── registry.json              ← materialized view (NOT source of truth)
├── transitions/               ← canonical source of truth (append-only)
│   └── {timestamp}_{rule_id}_{from}_{to}.json
├── artifacts/                 ← versioned per transition
│   └── {rule_id}/
│       └── {transition_id}/
│           ├── constraint_validation.json    (D8)
│           ├── semantic_review.json          (D8)
│           ├── derivation_test.json          (D4)
│           └── auditor_assessment.json       (D9)
└── audit/                     ← free-text, not in runtime payload
    └── {rule_id}/
        └── provenance.md
```

Authority chain: `transitions/` → derives → `registry.json`. `artifacts/` → indexed
by → `transition_id`. `audit/` → not consumed by runtime.

**Classification**: Judgment call — JSON vs SQLite is implementation preference, nhưng
authority relation và artifact versioning là structural requirements (Thiếu sót đã sửa).

**Status**: Open (pending codex §7 evaluation).

---

## Stage 1B Summary

10/12 issues **Converged** (confirmed in this round):
MK-09, MK-10, MK-11, MK-12, MK-14, MK-15, C3, C4, C5, C6.

2/12 issues **Open** with revised proposals:
- MK-08: 3-axis separation (constraint/semantic/lifecycle) + `RETIRED → PROPOSED`
  re-entry law (no shortcuts).
- MK-13: transition log canonical (registry = materialized view) + artifacts versioned
  per transition (no singleton overwrite).

Cả hai sửa đổi không mở surface mới: chúng tighten thiết kế đã đề xuất ở round 4
theo đúng hai lỗ hổng codex nêu, không thay đổi direction hay thêm component.

---

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|----------|-------|-----------|------------|---------------------|------------------------|
| X38-MK-08 | Lesson lifecycle | Thiếu sót | **Open** | — | Revised: 3-axis + re-entry law. Pending codex §7 |
| X38-MK-09 | Challenge process | Thiếu sót | **Converged** | V1 phải có `follow-rule-then-challenge` runtime law để giữ protocol lock | `MK-17` làm empirical priors shadow-only trong v1; challenge runtime thuộc v2+ và phụ thuộc `MK-16` + `D3` + `MK-08` |
| X38-MK-10 | Expiry mechanism | Thiếu sót | **Converged** | Cần decay/counter ngay để tránh Tier 2 bất tử | Threshold không có primitive rõ và `D1` cấm retirement ngầm; counter chỉ có thể trigger review |
| X38-MK-11 | Conflict resolution | Thiếu sót | **Converged** | Top-`k` heuristic practical enough làm conflict model ban đầu | Ranking ≠ conflict semantics; v1 không có active empirical priors |
| X38-MK-12 | Confidence scoring | Judgment call | **Converged** | Scalar là cần thiết để modulate force/budget/staleness | Scalar chỉ là stealth confidence; epistemic state nên qualitative, numeric knobs chỉ là operational defaults |
| X38-MK-13 | Storage format | Judgment call | **Open** | — | Revised: transition log canonical + artifact versioning. Pending codex §7 |
| X38-MK-14 | Firewall boundary | Thiếu sót | **Converged** | Symmetric cleanliness API đủ để nối Topic 002 và 004 | `D7` đòi content gate và governance gate tách ownership; proposal mới đã phân vai đúng |
| X38-MK-15 | Bootstrap problem | Judgment call | **Converged** | Phải chọn zero/Tier1-only/LEGACY để tránh leak mà vẫn giữ knowledge | `MK-17` đã tách influence khỏi seeding; provenance metadata + `SHADOW` giải bài toán mà không cần tier mới |
| C3 | Budget split | Thiếu sót | **Converged** | Fixed split nên thay bằng configurable/adaptive split | V1 không có frontier/probe split; nếu quay lại ở v2+ phải chịu burden of proof về disconfirming coverage |
| C4 | Overlap guard | Sai thiết kế | **Converged (superseded by MK-17)** | Eval-overlap-only guard giữ được useful same-asset learning | `MK-17` chốt same-dataset empirical priors đều shadow-only; x37 evidence yêu cầu appended data mới cho clean resolution |
| C5 | Active cap | Thiếu sót | **Converged** | Giữ active cap nhưng thay `novelty distance` bằng `scope + evidence` | Vẫn là attention-management heuristic, không phải conflict model; v1 cũng không cần active cap |
| C6 | V1 complexity scope | Thiếu sót | **Converged** | Stage complexity nhưng vẫn giữ một phần overlap/challenge runtime trong v1 | `MK-17` làm phần runtime đó vô giá trị ở v1; điều phải freeze ngay là governance invariants |
