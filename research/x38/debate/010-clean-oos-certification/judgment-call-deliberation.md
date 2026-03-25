# Judgment Call Deliberation — X38-D-23

**Topic**: 010 — Clean OOS & Certification
**Issue**: X38-D-23 — Pre-existing candidates vs x38 winners
**Decision owner**: Human researcher
**Date**: 2026-03-25
**Round closed**: 6 (§14 — max_rounds reached)

---

## Decision

**Accept Claude Code position.** Rationale per scenario:

### Scenario 1 — Same-family rediscovery

Defer same-family rediscovery lookup semantics to **Topic 008 / F-13**. Topic
010 does not own family-identity lookup fields or same-family equivalence
semantics. If Topic 008 later exports a same-family relation, Topic 010 may
consume it only for **below-certification convergence signaling**; Clean OOS is
still required and there is **no automatic certification uplift**.

### Scenario 2 — Contradiction

Keep the already-settled rule: contradiction with historical lineage **MUST be
surfaced explicitly** below certification tier (Topic 007 semantic rule).

### Scenario 3 — NO_ROBUST_IMPROVEMENT with pre-existing candidate

Freeze an explicit derived invariant: if shadow provenance contains a
pre-existing candidate and the x38 campaign verdict is `NO_ROBUST_IMPROVEMENT`,
then that pre-existing candidate remains **unchanged / unadjudicated by x38**,
below certification tier. This is not certification, not contradiction, and does
not create a new x38 winner.

---

## Both positions (§14 record)

- **Claude Code**: Topic 010 is complete once shadow-only provenance,
  contradiction surfacing, and x38-only certification are frozen; Scenario 1
  deferred to Topic 008 identity schema; Scenario 3 frozen as derived invariant.
- **Codex**: Topic 010 should freeze the below-certification relation / lookup
  contract for Scenario 1 and the Scenario 3 null state as an explicit contract
  before topic closure.

## Why judgment is not biased by author position (§16)

Decision owner (human researcher) is not a debate participant. The decision
follows the V1 design principle applied throughout Topic 010: freeze
obligations that sources back, defer specifics that depend on unresolved
cross-topic schemas. Topic 008 F-13 (identity axes) is genuinely Open and
outside Topic 010's authority.
