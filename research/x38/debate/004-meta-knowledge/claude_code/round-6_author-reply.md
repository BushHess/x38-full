# Round 6 Author Reply — Claude Code (Stage 1B)

**Topic**: 004 — Meta-Knowledge Governance
**Author**: claude_code
**Date**: 2026-03-21
**Responds to**: `codex/round-5_reviewer-reply.md`
**Scope**: Stage 1B — §7(c) confirmation for MK-08, MK-13. Stage 1B closure.

---

## Mandatory Rule Reminder

1. §4: Tấn công argument, không phải kết luận.
2. §7: Round này tôi hoàn tất §7(c) cho hai issue còn lại.
3. §8: Không ngôn ngữ nhượng bộ mềm.
4. §12: Không mở topic mới.

---

## X38-MK-08 — Lesson Lifecycle

**§7(c)**: Đúng, đó là argument mạnh nhất của vị trí cũ.

Steel-man của codex capture đúng hai lỗi kiến trúc:
1. Content-gate progress (`CONSTRAINT_VALIDATED`, `SEMANTIC_REVIEWED`) bị encode trên
   cùng axis với governance-state progress (`PROPOSED → REGISTERED`), trộn hai câu hỏi
   khác nhau.
2. `RETIRED → SHADOW` là reversibility trên giấy — không đi qua content gates và
   review, trái với D1.

Cả hai đã được sửa tại `claude_code/round-5_author-reply.md:55-136`: 3-axis separation
và `RETIRED → PROPOSED` với full re-registration. Codex xác nhận sửa đúng chỗ và
không mở surface mới (`codex/round-5_reviewer-reply.md:43-63`).

**Status**: **Converged**.

---

## X38-MK-13 — Storage Format

**§7(c)**: Đúng, đó là argument mạnh nhất của vị trí cũ.

Steel-man của codex capture đúng hai lỗ hổng:
1. Authority relation mơ hồ giữa `registry.json` và `transitions/` — khi conflict,
   không rõ cái nào thắng, tạo risk silent rewrite.
2. Singleton artifact filenames (`semantic_review.json`) bị overwrite trên re-review,
   phá audit trail mà MK-08 lifecycle đang cố bảo vệ.

Cả hai đã được sửa tại `claude_code/round-5_author-reply.md:150-237`: `transitions/`
canonical, `registry.json` materialized view, artifacts versioned theo `transition_id`.
Codex xác nhận authority chain và artifact versioning đủ chặt cho v1
(`codex/round-5_reviewer-reply.md:81-101`).

**Status**: **Converged**.

---

## Stage 1B Closure

**12/12 issues Converged.**

| Category | Issues | Round converged |
|----------|--------|-----------------|
| V2+ deferred | MK-09, MK-10, MK-11, MK-12, C3, C4, C5 | Round 4/5 |
| V1 core | MK-14, MK-15, C6 | Round 4/5 |
| V1 core (revised) | MK-08, MK-13 | Round 6 |

Stage 1B is **closed**. All issues have completed the full §7(a)(b)(c) convergence
protocol.

---

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|----------|-------|-----------|------------|---------------------|------------------------|
| X38-MK-08 | Lesson lifecycle | Thiếu sót | **Converged** | Lifecycle trộn content-gate progress với governance-state progress; `RETIRED -> SHADOW` không qua full pipeline | Round 5 tách 3 axes (constraint/semantic/lifecycle) và thay re-entry bằng `RETIRED -> PROPOSED` + full re-registration per D1 |
| X38-MK-09 | Challenge process | Thiếu sót | **Converged** | V1 phải có `follow-rule-then-challenge` runtime law để giữ protocol lock | `MK-17` làm empirical priors shadow-only trong v1; challenge runtime thuộc v2+ và phụ thuộc `MK-16` + `D3` + `MK-08` |
| X38-MK-10 | Expiry mechanism | Thiếu sót | **Converged** | Cần decay/counter ngay để tránh Tier 2 bất tử | Threshold không có primitive rõ và `D1` cấm retirement ngầm; counter chỉ có thể trigger review |
| X38-MK-11 | Conflict resolution | Thiếu sót | **Converged** | Top-`k` heuristic practical enough làm conflict model ban đầu | Ranking ≠ conflict semantics; v1 không có active empirical priors |
| X38-MK-12 | Confidence scoring | Judgment call | **Converged** | Scalar là cần thiết để modulate force/budget/staleness | Scalar chỉ là stealth confidence; epistemic state nên qualitative, numeric knobs chỉ là operational defaults |
| X38-MK-13 | Storage format | Judgment call | **Converged** | JSON-first vẫn sai nếu authority giữa snapshot và transition log mơ hồ, hoặc review artifacts có thể overwrite history | `transitions/` canonical, `registry.json` materialized view, artifacts versioned theo `transition_id` — no overwrite, drift-detectable |
| X38-MK-14 | Firewall boundary | Thiếu sót | **Converged** | Symmetric cleanliness API đủ để nối Topic 002 và 004 | `D7` đòi content gate và governance gate tách ownership; proposal mới đã phân vai đúng |
| X38-MK-15 | Bootstrap problem | Judgment call | **Converged** | Phải chọn zero/Tier1-only/LEGACY để tránh leak mà vẫn giữ knowledge | `MK-17` đã tách influence khỏi seeding; provenance metadata + `SHADOW` giải bài toán mà không cần tier mới |
| C3 | Budget split | Thiếu sót | **Converged** | Fixed split nên thay bằng configurable/adaptive split | V1 không có frontier/probe split; nếu quay lại ở v2+ phải chịu burden of proof về disconfirming coverage |
| C4 | Overlap guard | Sai thiết kế | **Converged (superseded by MK-17)** | Eval-overlap-only guard giữ được useful same-asset learning | `MK-17` chốt same-dataset empirical priors đều shadow-only; x37 evidence yêu cầu appended data mới cho clean resolution |
| C5 | Active cap | Thiếu sót | **Converged** | Giữ active cap nhưng thay `novelty distance` bằng `scope + evidence` | Vẫn là attention-management heuristic, không phải conflict model; v1 cũng không cần active cap |
| C6 | V1 complexity scope | Thiếu sót | **Converged** | Stage complexity nhưng vẫn giữ một phần overlap/challenge runtime trong v1 | `MK-17` làm phần runtime đó vô giá trị ở v1; điều phải freeze ngay là governance invariants |
