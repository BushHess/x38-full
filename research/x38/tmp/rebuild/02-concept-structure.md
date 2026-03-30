# 02 — Concept-Based Structure

> Solves: B-01, B-02, B-03, B-04, B-05, B-06, D-06
> Status: DRAFT

---

## Problem Summary

Current structure: 19 debate topics organized by **process** (when/how things were debated).
Result: Same concept scattered across 3-5 topics. Understanding "firewall" requires reading 5 different final-resolution.md files.

Additionally:
- Findings within topics that should be merged (B-03: 011 has 4 where 2 suffice)
- Contradictions between topics not surfaced (B-02: 015 vs 011 on sizing)
- Bidirectional dependencies without ordering (B-06: 005 vs 014)

---

## Solution: Reorganize from 19 topics to 9 concept domains

### New structure

```
x38/decisions/
├── 01-philosophy.md
├── 02-campaign-model.md
├── 03-identity-versioning.md
├── 04-firewall.md
├── 05-meta-knowledge.md
├── 06-clean-oos.md
├── 07-convergence.md
├── 08-search-expansion.md
└── 09-open-questions.md
```

### Mapping: Old topics -> New domains

> **AUDIT NOTE (2026-03-29)**: Original estimates ("~8", "~10") were speculative.
> Self-audit against actual data shows severe undercounting. Corrected below.
> Exact counts require full extraction — estimates now based on actual topic sizes.

| New domain | Sources (old topics) | Est. findings | Audit note |
|------------|---------------------|---------------|------------|
| 01-philosophy | 007 | 4 | Accurate (007 has exactly 4) |
| 02-campaign-model | 001 (7), parts of 010, parts of 013 | 12-15 | Was "~8" — 001 alone has 7 |
| 03-identity-versioning | 008 (4), parts of 011 (6), parts of 015 (11) | 15-21 | Was "~8" — SEVERELY understated |
| 04-firewall | 002 (8), parts of 004 | 12-15 | Was "~10" — 002 alone has 8 |
| 05-meta-knowledge | 004 (26), parts of 002 | 20-26 | Was "~12" — 004 has 26 findings! |
| 06-clean-oos | 010 (4), parts of 001 | 5-7 | Was "~6" — roughly correct |
| 07-convergence | 013 (15), parts of 018 | 15-18 | Was "~8" — 013 has 15 findings |
| 08-search-expansion | 018 (11), routing table | 11-13 | Was "~11" — roughly correct |
| 09-open-questions | All DEFERRED items, contradictions | variable | N/A — tracking file |

**Imbalance risk**: 05-meta-knowledge (20-26) and 03-identity-versioning (15-21)
are very large. Consider splitting if extraction confirms >20 findings in one domain.
Possible splits:
- 05-meta-knowledge → 05a-meta-taxonomy + 05b-meta-lifecycle (if >20)
- 03-identity-versioning → 03a-identity-schema + 03b-versioning-rules (if >20)

### What happens to open topics (003, 005, 006, 009, 011, 012, 014, 015, 016, 017)

Open topic findings are **not yet decisions**. They go into the relevant domain file under a separate `## Open` section:

| Old open topic | New domain | Findings |
|----------------|-----------|----------|
| 003 (protocol engine) | New domain: `10-protocol-engine.md` (kept separate — integration hub) |
| 005 (core engine) | `11-engine-design.md` (merged with 014) |
| 006 (feature engine) | `08-search-expansion.md` (SSE-D-03) + new `12-feature-engine.md` (F-08) |
| 009 (data integrity) | `03-identity-versioning.md` or standalone `13-data-integrity.md` |
| 011 (deployment) | `03-identity-versioning.md` (F-28/F-29) + `14-deployment.md` (F-26/F-27) |
| 012 (QA) | `15-quality-assurance.md` (F-18 only; F-19 becomes supporting evidence) |
| 014 (execution) | `11-engine-design.md` (merged with 005 — solves B-06) |
| 015 (artifact versioning) | `03-identity-versioning.md` (F-17 merged with 011 F-28/F-29 — solves B-02) |
| 016 (recalibration) | `16-bounded-recalibration.md` (cross-cutting, kept separate) |
| 017 (epistemic search) | `17-epistemic-search.md` (cross-cutting, kept separate) |

### Resolving specific issues

**B-02 (015 vs 011 sizing conflict)**:
Both F-17 and F-28 move into `03-identity-versioning.md`. This makes the contradiction
**visible** in 1 file — but **does NOT resolve it**. Both positions remain OPEN.

> **AUDIT NOTE (2026-03-29)**: Original plan claimed moving to same file = "resolved".
> This is WRONG. Colocation surfaces the problem but doesn't decide it.
> The rebuild must explicitly mark this as:
> - `## Open` finding: "X38-IDV-??: Sizing ownership — algo_version (F-17) vs deploy_version (F-28)"
> - Both positions documented with evidence
> - MUST be decided during domain debate, not deferred
> - The merged finding blocks: architecture_spec §8, 03-identity-versioning INTEGRATED status

**B-03 (011 has 4 findings, should be 2)**:
- F-27 (boundary) + F-28 (unit-exposure) + F-29 (version split) -> merge into 1 multi-part finding in `03-identity-versioning.md`
- F-26 (monitoring trigger) -> stays separate in `14-deployment.md`

**B-04 (015 mixed provenance)**:
- F-14, F-17 -> `03-identity-versioning.md` under `## Open`
- SSE-07, SSE-08, SSE-04-INV -> same file under `## Constraints` (imported from 018)

**B-05 (006 orphaned finding)**:
- F-08 + SSE-D-03 merged into single finding in `12-feature-engine.md`: "Feature engine design: registry pattern + generation mode acceptance"

**B-06 (005 vs 014 circularity)**:
Both merged into `11-engine-design.md`. Single file = single ordering. Engine API decision (from 005) comes first, execution orchestration (from 014) second.

**D-06 (19 topics too many)**:
Reduced to ~12 concept domains. Open questions consolidated. Process overhead drops.

---

## Domain file format

Each domain file follows this structure:

```markdown
# {Domain Name}

## Decided (from closed debates)

### X38-{DOM}-01: {Title}
- **Decision**: {1-2 sentence summary}
- **Type**: CONVERGED | ARBITRATED | AUTHORED | DEFAULT
- **Source**: Topic {NNN}, Round {N}
- **Rationale**: {Why this position won — 1 sentence for CONVERGED, 2-3 for ARBITRATED}
- **Consumed by**: {spec section(s)}

### X38-{DOM}-02: ...

## Constraints (imported from other domains)

### X38-{OTHER}-NN: {Title}
- **Decision**: {summary}
- **Imported from**: {domain file}
- **Impact on this domain**: {how it constrains decisions here}

## Open (not yet decided)

### X38-{DOM}-NN: {Title}
- **Question**: {the design choice}
- **Positions**: A: ... / B: ...
- **Depends on**: {other findings}
- **Blocks**: {spec sections}

## Deferred

### X38-{DOM}-NN: {Title}
- **Blocked by**: {finding ID or domain}
- **Unblocks**: {spec section}
- **Provisional value**: {if any}
```

---

## Verify Checklist

- [ ] All 48 CONVERGED findings placed in correct domain
- [ ] All 17 reclassified JCs placed in correct domain
- [ ] B-02 contradiction visible in single file (03-identity-versioning.md)
- [ ] B-03 merged: 011 F-27/F-28/F-29 -> 1 multi-part finding
- [ ] B-04 resolved: 015 native vs imported clearly separated
- [ ] B-05 merged: 006 F-08 + SSE-D-03
- [ ] B-06 resolved: 005 + 014 in single file with ordering
- [ ] Each domain file follows standard format
- [ ] No finding appears in 2 domain files (except as CONSTRAINT cross-ref)
- [ ] Topic count reduced from 19 to ~12 concept domains
