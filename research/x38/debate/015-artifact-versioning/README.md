# Topic 015 — Artifact & Version Management

**Topic ID**: X38-T-15
**Opened**: 2026-03-22
**Status**: OPEN
**Origin**: Split từ Topic 003 — F-14 và F-17 có bản chất "records & versioning",
khác với F-05 (pipeline logic). Tách để giảm tải 003 và cho phép debate sớm hơn
(Wave 2 thay vì Wave 3).

## Scope

Session artifact enumeration (state pack) và semantic change classification
(khi nào code changes invalidate kết quả). Cả hai về cùng concern: **cái gì
được ghi lại và khi nào nó mất hiệu lực**.

Topic 003 (Protocol Engine) định nghĩa **pipeline stages chạy thế nào**.
Topic 015 định nghĩa **ghi lại cái gì** (F-14) và **khi nào kết quả bị
vô hiệu hóa** (F-17).

**Findings**:
- F-14: State pack specification — session artifact enumeration (từ gen4)
- F-17: Semantic change classification (từ gen4)

**Convergence notes liên quan** (shared reference tại `000-framework-proposal/`):
- C-05: Semantic boundary DIAGNOSIS hội tụ; exact boundary cần debate
- C-12: Bounded recalibration prima facie bất tương thích (liên quan F-17)

## Dependencies

- **Upstream**: Topic 007 (philosophy — scope phải settled trước),
  Topic 008 (architecture — directory structure ảnh hưởng artifact layout)
- **Downstream**: Topic 003 (protocol engine — artifact spec inform stage outputs),
  Topic 014 (execution — checkpointing cần biết artifact format)

## Debate plan

- Ước lượng: 1-2 rounds
- Key battles:
  - F-14: Bao nhiêu artifacts mandatory vs optional? Hash manifest per-session?
    Auto-generated summary hay human-written?
  - F-17: Bit-identical test khả thi? Invalidation scope (toàn bộ hay chỉ affected)?
    Auto re-run hay manual trigger?

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 003 | F-05 | Protocol stages define WHEN artifacts are produced; F-14 defines WHAT is produced — if 003 changes stage boundaries, artifact enumeration may need updating | 003 owns stage structure; 015 adapts artifact spec |
| 011 | F-28 | F-17 classifies sizing change as semantic change (new version), but F-28 proposes unit-exposure canonicalization pushing sizing to deployment — if adopted, F-17 classification table must be amended | 011 owns boundary decision (F-28); 015 amends F-17 accordingly |
| 016 | C-12 | Bounded recalibration (if adopted) may create semantic changes mid-campaign that F-17 must classify — current classification assumes freeze-once model | 016 owns decision |

## Files

| File | Mục đích |
|------|----------|
| `findings-under-review.md` | 2 findings: F-14, F-17 |
| `claude_code/` | Phản biện từ Claude Code |
| `codex/` | Phản biện từ Codex |
