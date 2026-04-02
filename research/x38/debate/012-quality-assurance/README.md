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
- F-39: Framework testing strategy — automated correctness assurance (gap audit 2026-03-31)
- F-19: Online framework evolution — gen2→gen3→gen4 failure modes (**DEMOTED** to supporting evidence, 2026-03-31)

## Dependencies

- **Upstream**: Topic 007 (philosophy), Topic 008 (architecture — module dependency graph)
- **Downstream**: Mọi implementation phase (quality gates áp dụng cho toàn bộ code)

## Debate plan

- Ước lượng: 1 round
- Key battles:
  - F-18: Formal checklist vs lightweight approve/reject? Test coverage threshold?
  - F-19: Gen3 failure modes (zero-trade trap, MDD cap) có xuất hiện trong offline?

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 005 | F-07 | Engine design (vectorized vs event-loop) determines testing strategy | 005 owns engine design; 012 adapts testing strategy |
| 003 | F-05 | Pipeline integration tests need stage definitions finalized | 003 owns stages; 012 designs integration tests against stage contracts |
| 002 | F-04 | Firewall testing needs typed schema spec finalized | 002 CLOSED; 012 tests against 002's confirmed contracts |

## Files

| File | Mục đích |
|------|----------|
| `findings-under-review.md` | 2 active findings: F-18, F-39 + F-19 (demoted to supporting evidence) |
| `claude_code/` | Phản biện từ Claude Code |
| `codex/` | Phản biện từ Codex |
