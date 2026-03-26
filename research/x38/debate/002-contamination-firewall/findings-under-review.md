# Findings Under Review — Contamination Firewall

**Topic ID**: X38-T-02
**Opened**: 2026-03-22 (activated from PLANNED)
**Author**: claude_code (architect)

1 finding về machine-enforced contamination firewall.

**Convergence notes liên quan** (full text tại `../000-framework-proposal/findings-under-review.md`
§Pre-Debate Convergence Notes):
- C-01: MK-17 ≠ primary evidence chống bounded recalibration. Trụ chính = firewall
- C-10: F-01 cần operationalize qua firewall, không standalone
- C-11: Authority chain: design_brief + PLAN primary, F-04 supporting enforcement
- C-12: Bounded recalibration prima facie bất tương thích với current firewall

**Cross-topic references**:
- Topic 004 (CLOSED) MK-14 boundary contract —
  firewall ↔ meta-knowledge interface. Xem `../004-meta-knowledge/final-resolution.md`.
- Topic 004 (CLOSED) MK-07 (AMENDED 2026-03-23) — F-06 category coverage
  investigation found ~10 Tier 2 structural priors with no category home.
  Original interim rule "ambiguous → non-admissible" blocks rules that should be
  admitted. Revised to distinguish GAP vs AMBIGUITY. **Final fix resolved by Topic 002 closure (2026-03-25)**: no category expansion;
  permanent `UNMAPPED + Tier 2 + SHADOW` governance path chosen (second fork).
  Evidence: `input_f06_category_coverage.md` (pre-debate input, ~80+ rules mapped).
  Resolution: `final-resolution.md` §Decision 4, §Decision 5.

---

## F-04: Contamination firewall — machine-enforced

- **issue_id**: X38-D-04
- **classification**: Thiếu sót
- **opened_at**: 2026-03-18
- **opened_in_round**: 0
- **current_status**: Resolved (3 Converged + 4 Judgment call, round 6, 2026-03-25)

**Nội dung**:

Đề xuất enforcement cụ thể:

**A. Typed schema + whitelist category** (thay cho free-text + regex):

Regex không bắt được semantic leakage (ví dụ: "the efficiency-based approach
works well" không match regex nhưng vẫn leak answer prior). Thay vào đó:

```
MetaLesson {
    id: str
    category: enum  # V1 whitelist (post Facet C convergence: 3 categories):
                    #   PROVENANCE_AUDIT_SERIALIZATION,
                    #   SPLIT_HYGIENE, ANTI_PATTERN
                    # (STOP_DISCIPLINE consolidated into ANTI_PATTERN
                    #  per debate Round 2 — see final-resolution.md §Decision 1)
    principle: str  # Validated against whitelist categories
    confidence: float
    confirmed_by: list[str]
    contradicted_by: list[str]
    status: enum  # ACTIVE, RETIRED, CONTESTED
}
```

Category whitelist enforcement: lesson với category ngoài whitelist bị reject.
Lesson có nội dung thuộc family/architecture/calibration-mode phải bị reject
cho mapped categories và genuine ambiguity — cần human review nếu ambiguous.
Pure-gap structural priors (no category fits) đi theo permanent `UNMAPPED +
Tier 2 + SHADOW` governance path per Topic 004 MK-07 amendment và Topic 002
closure (`final-resolution.md` §Decision 4).

**B. State machine ký hash cho protocol transitions:**
- Mỗi stage transition được ký bằng hash của artifacts hiện có
- Contamination log chỉ readable SAU KHI frozen_spec.json hash tồn tại
- State machine ngăn rollback (FROZEN → SCANNING là transition bất hợp lệ)

**C. Filesystem read-only là guardrail phụ:**
- chmod 444 sau verdict — defense-in-depth, không phải primary enforcement
- Primary enforcement là state machine + typed schema

**Evidence**:
- CONTAMINATION_LOG_V4.md [extra-archive]: 8 rounds đã contaminate toàn bộ file — proof rằng
  honor-based isolation không đủ.
- PROMPT_FOR_V7_HANDOFF.md line 142-175 [extra-archive]: 10-item checklist kiểm tra contamination leak.

**Câu hỏi mở**:
- Typed schema có quá restrictive? Lesson hợp lệ nhưng không fit categories?
- Human review cho ambiguous cases: workflow ra sao?
- State machine complexity: quá phức tạp cho v1 framework?
- (Added 2026-03-23, from MK-07 investigation) 3 categories (post Facet C) thiếu chỗ cho ~10
  Tier 2 structural priors — cần thêm category (e.g., `STRUCTURAL_PRIOR`) hay
  redefine existing? Xem `input_f06_category_coverage.md` §9 Finding A.
- (Added 2026-03-23) `PROVENANCE_AUDIT_SERIALIZATION` overloaded (~25+ rules) —
  cần split thành finer-grained categories? Xem Finding D.
- (Added 2026-03-23, **RESOLVED Round 2**: consolidate vào `ANTI_PATTERN` — Facet C
  Converged. Xem Finding C + `final-resolution.md` §Decision 1.)

---

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 004 | MK-07 | F-06 category coverage gap: ~10 Tier 2 structural priors have no category home in F-04 whitelist. **RESOLVED**: permanent `UNMAPPED + Tier 2 + SHADOW` path chosen. No category expansion | **RESOLVED** within this topic (2026-03-25) |
| 004 | MK-14 | Boundary contract between firewall and meta-knowledge interface — firewall enforcement must not block legitimate MK updates | 004 closed; residual interface constraint owned within this topic |
| 009 | F-11 | Session immutability (chmod) vs contamination firewall (typed schema + state machine) — two enforcement mechanisms for overlapping concerns, risk of conflicting rules | 009 owns immutability mechanism; 002 owns firewall mechanism |
| 016 | C-12 | Bounded recalibration prima facie incompatible with current firewall design — recalibration may require loosening firewall categories | 016 owns decision |
| 017 | ESP-02 | Reconstruction-risk gate extends firewall to phenotype layer: descriptor bundles that de facto identify a winner = contamination. No 5th category added; gap rules via `UNMAPPED` governance. | 002 gap fix **RESOLVED** (no category expansion); 017 defines phenotype contracts + reconstruction-risk gate within existing 3-category + UNMAPPED boundary (3 after STOP_DISCIPLINE→ANTI_PATTERN consolidation, Facet C). |

## Bảng tổng hợp

| Issue ID | Finding | Phân loại | Status |
|----------|---------|-----------|--------|
| X38-D-04 | Contamination firewall — machine-enforced | Thiếu sót | **Resolved** (3 Converged + 4 Judgment call, closed 2026-03-25, round 6) |
