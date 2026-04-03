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
- F-38: Feature interaction & conditional logic (gap audit 2026-03-31)
- SSE-D-03: Registry acceptance for auto-generated features (từ Topic 018)

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

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 017A/017B | ESP-01 (017A), ESP-02 (017B) | Phenotype descriptor taxonomy (017A/017B) overlaps feature family taxonomy (006). Both define how to categorize/tag strategies and features. | 006 owns feature-level taxonomy; 017A owns strategy-level descriptors, 017B owns phenotype contracts. Must not conflict. |
| 018 | SSE-D-03 | `generation_mode` feeds registry acceptance — registry must accept auto-generated features from `grammar_depth1_seed`. Routed from Topic 018 (CLOSED 2026-03-27). | 006 owns registry acceptance rules; 018 provides generation mode contract (confirmed). |

## Files

| File | Mục đích |
|------|----------|
| `findings-under-review.md` | 3 findings: F-08, F-38 + SSE-D-03 (from Topic 018) |
| `claude_code/` | Phản biện từ Claude Code |
| `codex/` | Phản biện từ Codex |
