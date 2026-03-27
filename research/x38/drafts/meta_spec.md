# Meta-Knowledge Governance Spec — Draft

**Status**: SEEDED (from Topics 002, 004, 007, 008 closures — 2026-03-27)
**Last updated**: 2026-03-27
**Dependencies**: 002(CLOSED) + 004(CLOSED) + 007(CLOSED) + 008(CLOSED)
**Publishable when**: ALL dependencies CLOSED (**all 4 deps now CLOSED** — eligible for DRAFTING phase)

---

## 1. 3-Tier Rule Taxonomy (Topic 004)

> Source: `debate/004-meta-knowledge/final-resolution.md` §MK-05

| Tier | Definition | Governance |
|------|-----------|------------|
| Tier 1 | Axiom — derivable from first principles | No shadow constraint |
| Tier 2 | Structural prior — empirical observation elevated to methodology | Tier 2 + SHADOW per MK-17 |
| Tier 3 | Session-scoped — observation from a specific session | Auto-expire |

---

## 2. Lesson Lifecycle (Topic 004)

> Source: `debate/004-meta-knowledge/final-resolution.md` §MK-08

Three independent axes: `constraint_status`, `semantic_status`, `lifecycle_state`.
Gate: PROPOSED → REGISTERED requires constraint=PASSED AND semantic=REVIEWED.

_Stub — full state machine from Topic 004 §V1 Lifecycle State Machine._

---

## 3. Storage Law (Topic 004)

> Source: `debate/004-meta-knowledge/final-resolution.md` §MK-13

`transitions/` = canonical source of truth. `registry.json` = materialized view.
Artifacts versioned per `transition_id`.

_Stub — full directory structure from Topic 004 §V1 Storage Structure._

---

## 4. Derivation Test (Topic 004)

> Source: `debate/004-meta-knowledge/final-resolution.md` §MK-04

Human-performed admissibility lens. "Partially" verdict requires structured artifact:
`first_principles_core`, `empirical_residue`, `admissibility_rationale`, `reviewer`,
`timestamp`.

---

## 5. Firewall Content Rules (Topic 002 + MK-14 Interface)

> Source: `debate/002-contamination-firewall/final-resolution.md` §Decision 1
> Interface: `architecture_spec.md` §7.4 (MK-14 boundary contract)

### 5.1 Content Gate — 3 Whitelist Categories

| Category | Scope |
|----------|-------|
| `PROVENANCE_AUDIT_SERIALIZATION` | Provenance, audit trails, serialization, session independence, freeze protocols |
| `SPLIT_HYGIENE` | Data split integrity, holdout discipline, contamination-by-split |
| `ANTI_PATTERN` | Methodology-level anti-patterns + absorbed `STOP_DISCIPLINE` rules (framework iteration constraints) |

### 5.2 Catch-All Ban

Lesson with content in family/architecture/calibration-mode: rejected for mapped
categories and genuine ambiguity (`docs/design_brief.md` §3.1).

### 5.3 GAP/AMBIGUITY Permanent Law

- **GAP** (no category fits): permanent `UNMAPPED` + Tier 2 + SHADOW.
  `UNMAPPED` = governance tag (Topic 004), not content category.
- **AMBIGUITY** (multiple categories fit): non-admissible pending human review.

Source: Topic 004 MK-07 Addendum, second fork chosen by Topic 002.

---

## 6. Challenge & Expiry (Topic 004)

> Source: `debate/004-meta-knowledge/final-resolution.md` §MK-09, §MK-10

Both deferred to v2+. V1: challenge observations recorded only; lifecycle includes
`REVIEW_REQUIRED` as trigger target.

---

## 7. Bootstrap (Topic 004)

> Source: `debate/004-meta-knowledge/final-resolution.md` §MK-15

Classify V4→V8 lessons via derivation test, tag provenance, all Tier 2 = SHADOW
per MK-17. No LEGACY tier.

---

## 8. Protocol Version Impact on Meta-Knowledge (Topic 008)

> Source: `debate/008-architecture-identity/final-resolution.md` §Decision 3
> Cross-ref: `architecture_spec.md` §2.2 (protocol version identity)

### 8.1 Protocol Version and Meta-Knowledge Scope

`campaign.json` carries a mandatory `protocol_version` field (Topic 008 D-13).
This has two implications for meta-knowledge governance:

1. **Cross-protocol comparison flagging**: When convergence analysis compares
   campaigns with different `protocol_version` values, the comparison MUST be
   explicitly flagged. Meta-lessons derived from cross-protocol comparisons
   carry inherently lower confidence.

2. **Meta-Updater scope**: The Meta-Updater operates post-campaign. It may
   only update methodology-level lessons (provenance/audit, split hygiene,
   anti-patterns — per §5.1 content gate). The `protocol_version` field
   provides provenance for WHEN a lesson was generated, enabling future
   audit of whether lessons from older protocol versions remain valid after
   protocol changes.

### 8.2 Candidate Identity and Meta-Knowledge

Candidate-level identity (Topic 008 SSE-04-IDV) uses structural pre-bucket
fields (descriptor hash, parameter family, AST-hash subset). These fields
are NOT meta-knowledge — they are scan artifact metadata. The Meta-Updater
does not consume or update candidate identity fields. The boundary is:
- Meta-knowledge = methodology-level lessons (what the Meta-Updater writes)
- Candidate identity = structural facts about scan outputs (what convergence
  analysis and ESP consume)

This boundary aligns with MK-14 (Topic 004): the firewall separates
methodology from data-derived specifics. Candidate structural hashes are
data-derived and therefore outside meta-knowledge scope.

---

## Traceability

| Section | Issue ID | Source |
|---------|----------|--------|
| §1 3-Tier Taxonomy | X38-MK-05 | `debate/004-meta-knowledge/final-resolution.md` §Decided table |
| §2 Lesson Lifecycle | X38-MK-08 | `debate/004-meta-knowledge/final-resolution.md` §V1 Lifecycle |
| §3 Storage Law | X38-MK-13 | `debate/004-meta-knowledge/final-resolution.md` §V1 Storage |
| §4 Derivation Test | X38-MK-04 | `debate/004-meta-knowledge/final-resolution.md` §MK-04 decision |
| §5.1 Content Gate | X38-D-04 | `debate/002-contamination-firewall/final-resolution.md` §Decision 1 |
| §5.2 Catch-All Ban | X38-D-04 | `debate/002-contamination-firewall/final-resolution.md` §Facet E |
| §5.3 GAP/AMBIGUITY | X38-D-04 | `debate/002-contamination-firewall/final-resolution.md` §Decision 5 |
| §6 Challenge & Expiry | X38-MK-09, X38-MK-10 | `debate/004-meta-knowledge/final-resolution.md` §Decided table |
| §7 Bootstrap | X38-MK-15 | `debate/004-meta-knowledge/final-resolution.md` §Decided table |
| §8.1 Protocol Version Impact | X38-D-13 | `debate/008-architecture-identity/final-resolution.md` §Decision 3 |
| §8.2 Candidate Identity Boundary | X38-SSE-04-IDV | `debate/008-architecture-identity/final-resolution.md` §Decision 4 |
