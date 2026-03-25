# Topic 002 — Contamination Firewall

**Topic ID**: X38-T-02
**Opened**: 2026-03-22 (activated from PLANNED)
**Status**: **CLOSED** (2026-03-25)
**Rounds**: 6 / 6 (max_rounds). 3 Converged + 4 Judgment call.
**Resolution**: `final-resolution.md`
**Origin**: F-04 (summary in Topic 000)

## Scope

Machine-enforced contamination firewall: typed schema, whitelist categories,
state machine, filesystem enforcement. Tách cứng methodology khỏi data-derived
specifics.

**Findings**:
- F-04: Contamination firewall — machine-enforced

**Convergence notes liên quan** (shared reference tại `000-framework-proposal/`):
- C-01: MK-17 ≠ primary evidence chống bounded recalibration. Trụ chính = firewall
- C-10: F-01 cần operationalize qua firewall, không standalone
- C-11: Authority chain: design_brief + PLAN primary, F-04 supporting enforcement
- C-12: Bounded recalibration prima facie bất tương thích với current firewall

**Cross-topic links**:
- Topic 004 (CLOSED): MK-14 boundary contract — firewall ↔ meta-knowledge interface
- Topic 004 (CLOSED, AMENDED 2026-03-23): MK-07 — F-06 category coverage gap.
  ~10 Tier 2 structural priors have no category home. **RESOLVED by 002 closure**:
  no category expansion; permanent `UNMAPPED + Tier 2 + SHADOW` (second fork).
  Evidence: `input_f06_category_coverage.md`
- Topic 009: F-11 session immutability — khác enforcement mechanism (chmod vs typed schema)

## Dependencies

- **Upstream**: Topic 007 (philosophy), Topic 008 (architecture — F-02 pillars)
- **Downstream**: Topic 003 (protocol engine cần firewall enforcement), specs (meta_spec + architecture_spec)

## Debate outcome

- Rounds used: 6 / 6 (max_rounds reached)
- Key decisions:
  - Typed schema: 3 categories permanent (STOP_DISCIPLINE consolidated into ANTI_PATTERN per Facet C), no expansion (Facets A, E)
  - Human review: GAP/AMBIGUITY distinction permanent (Facet B-author)
  - State machine: acceptable for v1, hash-signing is core enforcement (Facet D)
  - UNMAPPED + Tier 2 + SHADOW: permanent governance for ~10 gap rules (Facet E)
  - chmod: defense-in-depth only (Facet F)

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 004 | MK-07 | F-06 category coverage gap: ~10 Tier 2 structural priors. **RESOLVED**: permanent `UNMAPPED + Tier 2 + SHADOW`, no category expansion | **RESOLVED** (2026-03-25) |
| 004 | MK-14 | Boundary contract between firewall and meta-knowledge interface — firewall enforcement must not block legitimate MK updates | 004 closed; residual interface constraint owned within this topic |
| 009 | F-11 | Session immutability (chmod) vs contamination firewall (typed schema + state machine) — two enforcement mechanisms for overlapping concerns, risk of conflicting rules | 009 owns immutability mechanism; 002 owns firewall mechanism |
| 016 | C-12 | Bounded recalibration prima facie incompatible with current firewall design — recalibration may require loosening firewall categories | 016 owns decision |

## Files

| File | Mục đích |
|------|----------|
| `final-resolution.md` | Closure document — all decisions |
| `findings-under-review.md` | 1 finding: F-04 (resolved) |
| `input_f06_category_coverage.md` | Pre-debate input: F-06 category coverage investigation (~75 V4-V8 rules mapped, 4 findings). From MK-07 amendment (2026-03-23) |
| `claude_code/` | Phản biện từ Claude Code |
| `codex/` | Phản biện từ Codex |
