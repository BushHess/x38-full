# Topic 006 — Feature Engine Design

**Topic ID**: X38-T-06
**Opened**: 2026-03-22 (activated from PLANNED)
**Status**: OPEN
**Origin**: F-08 (summary in Topic 000)

## Scope

Feature engine: registry pattern, family organization, threshold calibration
modes, exhaustive scan strategy, cross-timeframe alignment.

**Findings**:
- F-08: Feature engine — registry pattern

## Dependencies

- **Upstream**: Topic 007 (philosophy), Topic 008 (architecture — F-09 directory)
- **Downstream**: Specs (feature_spec.md)

## Debate plan

- Ước lượng: 1 round
- Key battles:
  - Decorator pattern vs config-driven (YAML)?
  - 1 file = 1 family vs 1 file = 1 feature?
  - 4 threshold modes đủ?
  - Exhaustive scan vs intelligent pruning?

## Cross-topic tensions

Không có tension đã biết tại thời điểm mở topic.

## Files

| File | Mục đích |
|------|----------|
| `findings-under-review.md` | 1 finding: F-08 |
| `claude_code/` | Phản biện từ Claude Code |
| `codex/` | Phản biện từ Codex |
