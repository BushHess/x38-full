# Topic 005 — Core Engine Design

**Topic ID**: X38-T-05
**Opened**: 2026-03-22 (activated from PLANNED)
**Status**: OPEN
**Origin**: F-07 (summary in Topic 000)

## Scope

Core backtest engine: rebuild vs vendor, vectorized vs event-loop, 6 modules,
regression test scope.

**Findings**:
- F-07: Core engine — rebuild từ đầu

## Dependencies

- **Upstream**: Topic 007 (philosophy), Topic 008 (architecture — F-09 directory, F-02 pillars)
- **Downstream**: Specs (engine_spec.md)

## Debate plan

- Ước lượng: 1 round
- Key battles:
  - Rebuild vs vendor 5 files rồi simplify?
  - Vectorized (numpy) vs event-loop?
  - Regression test scope đủ chưa?

## Cross-topic tensions

Không có tension đã biết tại thời điểm mở topic.

## Files

| File | Mục đích |
|------|----------|
| `findings-under-review.md` | 1 finding: F-07 |
| `claude_code/` | Phản biện từ Claude Code |
| `codex/` | Phản biện từ Codex |
