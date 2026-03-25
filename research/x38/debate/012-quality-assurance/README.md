# Topic 012 — Quality Assurance & Implementation Evidence

**Topic ID**: X38-T-12
**Opened**: 2026-03-22
**Status**: OPEN
**Split from**: Topic 000 (cross-cutting)

## Scope

Chất lượng implementation và bài học từ online framework evolution. Bao gồm:
module-level verification gates và evidence từ gen2→gen3→gen4 failure modes.

**Findings**:
- F-18: Continuous verification — module-level review gates
- F-19: Online framework evolution — gen2→gen3→gen4 failure modes

## Dependencies

- **Upstream**: Topic 007 (philosophy), Topic 008 (architecture — module dependency graph)
- **Downstream**: Mọi implementation phase (quality gates áp dụng cho toàn bộ code)

## Debate plan

- Ước lượng: 1 round
- Key battles:
  - F-18: Formal checklist vs lightweight approve/reject? Test coverage threshold?
  - F-19: Gen3 failure modes (zero-trade trap, MDD cap) có xuất hiện trong offline?

## Cross-topic tensions

Không có tension đã biết tại thời điểm mở topic.

## Files

| File | Mục đích |
|------|----------|
| `findings-under-review.md` | 2 findings: F-18, F-19 |
| `claude_code/` | Phản biện từ Claude Code |
| `codex/` | Phản biện từ Codex |
