# Topic 014 — Execution & Resilience

**Topic ID**: X38-T-14
**Opened**: 2026-03-22
**Status**: OPEN
**Origin**: Gap analysis — execution model chưa có topic riêng

## Scope

Mô hình thực thi pipeline: compute orchestration cho exhaustive scans,
checkpointing & crash recovery, và human interaction model (CLI).

Topic 003 (Protocol Engine) định nghĩa **logic** các stages (what).
Topic 014 định nghĩa **cách chúng chạy** đáng tin cậy (how): song song
hóa, khôi phục sau crash, và giao diện vận hành.

**Findings**:
- F-32: Compute orchestration cho exhaustive scans
- F-33: Pipeline checkpointing & crash recovery
- F-40: Session concurrency model (gap audit 2026-03-31, issue_id X38-ER-03)

**Convergence notes liên quan** (shared reference tại `000-framework-proposal/`):
- (không có convergence note trực tiếp — topic mới từ gap analysis)

## Dependencies

- **Upstream**: Topic 007 (philosophy — scope phải settled trước),
  Topic 005 (core engine — cần biết engine là gì trước khi orchestrate),
  Topic 003 (protocol engine — cần biết stages trước khi define execution)
- **Downstream**: Không — topic cuối cùng về mặt thực thi

## Debate plan

- Ước lượng: 1-2 rounds
- Key battles:
  - F-32: Multiprocessing local đủ hay cần distributed? Scale target?
  - F-33: Checkpoint granularity: per-stage vs per-config? Idempotency guarantee?

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 003 | F-05 | Execution model (F-32/F-33) depends on protocol stages being finalized — but 003 is Wave 3 (last), while 014 needs stage definitions to design orchestration and checkpointing | 003 owns stage definitions; 014 designs execution against preliminary stage structure |
| 005 | F-07 | Core engine rebuild (F-07) must be finalized before orchestration can design worker model — engine API (vectorized vs event-loop) determines parallelization strategy | 005 owns engine design; 014 adapts orchestration |

## Files

| File | Mục đích |
|------|----------|
| `findings-under-review.md` | 3 findings: F-32, F-33, F-40 (ER-03) |
| `claude_code/` | Phản biện từ Claude Code |
| `codex/` | Phản biện từ Codex |
