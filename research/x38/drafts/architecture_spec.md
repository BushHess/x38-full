# Architecture Spec — Draft

**Status**: DRAFT (seeded from Topic 001, 002, 004, 007 closures — 002 section added 2026-03-25)
**Last updated**: 2026-03-25
**Dependencies**: 001(CLOSED) + 002(CLOSED) + 004(CLOSED) + 007(CLOSED) + 008 + 009 + 010 + 011 + 013 + 016 + 017
**Publishable when**: ALL dependencies CLOSED

---

## 1. Campaign Model (Topic 001)

> Source: `debate/001-campaign-model/final-resolution.md`

### 1.1 Campaign Definition (X38-D-03 → final-resolution.md §Decision 1)

A campaign is defined by required properties, not container shape:

- **Grouping**: hierarchical grouping above sessions
- **Protocol/dataset boundary**: shared, fixed dataset (SHA-256 verified) + fixed protocol (locked before discovery)
- **Lineage**: provenance chain across campaigns
- **HANDOFF law**: structured transition between campaigns

Exact container shape (first-class object vs lightweight grouping) is an
architecture choice — both are compatible with the required properties.

Numeric convergence floors (sessions-per-campaign, same-data ceiling) deferred
to Topic 013 (convergence analysis).

### 1.2 Metric Scopes (X38-D-15 → final-resolution.md §Decision 2)

Three metric scopes:

| Scope | Boundary | Purpose |
|-------|----------|---------|
| Session | Single session | Candidate ranking within session |
| Campaign | N sessions within one campaign | Convergence analysis (F-03) |
| Cross-campaign / HANDOFF | Across campaigns | Transition justification + lineage accounting |

**V1 constraint**: Third scope (cross-campaign/HANDOFF) stays narrow — transition
justification and lineage accounting only (MK-17 shadow-only). Does NOT become
an active empirical ranking lane.

### 1.3 HANDOFF Law (X38-D-16 → final-resolution.md §Judgment)

#### 1.3.1 One-Way Invariant

`protocol_identity_change → new campaign boundary`

If protocol identity changes, a new campaign MUST be opened. The converse is not
required: a new campaign may be opened without protocol identity change (e.g.,
convergence stall).

#### 1.3.2 HANDOFF Package

- **Triggers**: `{convergence_stall, methodology_gap}`
- **Single principal hypothesis**: one methodology change per HANDOFF
- **Dossier**: convergence_summary, gap_evidence, proposed_change, firewall_ref (→ Topic 002)
- **Bounded scope**: exact numeric limits from Topic 013

#### 1.3.3 Same-Data Governance

Per `PLAN.md:500-506`:
- Same-file campaigns have a default ceiling
- Exceeding requires **explicit human override** with justification
- Mandatory purpose declaration per campaign
- Same-file methodological tightening ≠ clean OOS evidence

#### 1.3.4 Transition-Routing Contract

| Evidence on frozen baseline | Claimed basis | Action | Campaign purpose |
|---|---|---|---|
| bit-identical / comment-only | n/a | no transition | n/a |
| results changed + proven defect + protocol identity preserved | defect correction | open same-data corrective campaign; invalidate affected scope and rerun | `corrective_re_run` |
| results changed + methodology/search/gating/objective changed | new hypothesis / methodology gap | open HANDOFF campaign | `convergence_audit` |
| ambiguous or preservation unproven | disputed | default to HANDOFF campaign | `convergence_audit` |
| new data appended / Clean OOS fail restart | n/a | new-data restart | n/a |

**Burden of proof**: if protocol-identity preservation is not proven, default to
HANDOFF. Conservative by design.

**Note**: "results changed" = results relevant to the change scope — trade log
(engine changes), rankings (metrics changes), verdicts (protocol logic changes).
Consistent with F-17 semantic change classification (Topic 015).

#### 1.3.5 Campaign Purpose Labels

- **`corrective_re_run`**: corrects a proven defect without changing methodology intent. Protocol identity preserved.
- **`convergence_audit`**: (a) verifying independent session convergence, AND/OR (b) methodology advancement. Any same-data campaign that is NOT a corrective re-run.

#### 1.3.6 Cross-Topic Interfaces

| Interface | Owner | 001 consumes/provides |
|---|---|---|
| Protocol identity/version schema | Topic 008 (F-13) | 001 consumes: one-way invariant references identity |
| Protocol content | Topic 003 (F-05) | 001 consumes: routing contract references protocol definition |
| Stop thresholds, sessions-per-campaign | Topic 013 (F-31) | 001 provides: scope definitions, HANDOFF vocabulary |
| Evidence classes, invalidation scope | Topic 015 (F-17) | 001 consumes: routing contract maps evidence classes to actions |
| Recalibration exceptions | Topic 016 | 001 provides: HANDOFF mechanism + third scope definition |

---

## 2. Session Lifecycle

> Pending: Topic 008 (architecture & identity)

_Stub — to be filled after Topic 008 closure._

---

## 3. Directory Structure

> Pending: Topic 008

_Stub._

---

## 4. Data Management & Immutability

> Pending: Topic 009 (data integrity)

_Stub._

---

## 5. Claim Model & Evidence Taxonomy (Topic 007)

> Source: `debate/007-philosophy-mission/final-resolution.md`

### 5.1 Philosophy Invariant (X38-D-01 → final-resolution.md §Decision 1)

The framework's promise: find the strongest candidate WITHIN the declared search
space, or honestly conclude `NO_ROBUST_IMPROVEMENT`. It is NOT self-executing —
operationalization depends on the contamination firewall (C-10, Topic 002).

`NO_ROBUST_IMPROVEMENT` is a valid campaign-level verdict, not a failure mode.

### 5.2 3-Tier Claim Model (X38-D-20 → final-resolution.md §Decision 2)

| Tier | Claim | Verdict bearer | Verdicts |
|------|-------|----------------|----------|
| **Mission** | "Find the best algorithm" | None — charter framing, infinite-horizon aspiration | n/a |
| **Campaign** | Strongest leader within declared search space | Campaign output | `INTERNAL_ROBUST_CANDIDATE` / `NO_ROBUST_IMPROVEMENT` |
| **Certification** | Winner confirmed by independent evidence | Clean OOS | `CLEAN_OOS_CONFIRMED` / `CLEAN_OOS_INCONCLUSIVE` / `CLEAN_OOS_FAIL` |

Mission is NOT a peer tier in the verdict taxonomy — it is document-level framing
explicitly marked as non-verdict. Naming (Mission/Campaign/Certification vs
alternatives) is provisional until this spec is published.

### 5.3 Phase 1 Evidence Taxonomy (X38-D-22 → final-resolution.md §Decision 3)

Three evidence types frozen for Phase 1 on exhausted archives:

| Evidence type | Source | Claim ceiling |
|---------------|--------|---------------|
| **Coverage/process** | Same-archive exhaustive scan | "Features scanned converge on D1 family" |
| **Deterministic convergence** | Same-archive N sessions | "N sessions produce same leader" |
| **Clean adjudication** | New data (Phase 2) | Certification tier |

**Semantic rule**: if same-archive search (of either type) contradicts the
historical lineage, the artifact MUST surface that contradiction explicitly and
keep it below certification tier.

Sub-type taxonomy within same-archive categories is NOT frozen — open for Topics
001 and 010 to define. Divergence investigation protocol: shared ownership
between Topics 001 and 010.

### 5.4 Regime-Aware Policy Boundary (X38-D-25 → final-resolution.md §Decision 4)

**ALLOWED** (V1): A single frozen policy object with evidence-backed internal
conditional logic (e.g., D1 EMA(21) regime filter in E5_ema21D1).

**FORBIDDEN**:
- Per-regime parameter tables
- External framework-provided regime classifiers
- Post-freeze regime-based winner switching

V2+ extension path: regime-aware structure is a declared extension point
requiring empirical evidence of stationary failure + ablation gate specification
(Topic 003) + human researcher approval.

---

## 6. Clean OOS Flow

> Pending: Topic 010 (clean OOS & certification)
> Cross-ref: §5.2 certification tier, §5.3 evidence taxonomy

_Stub._

---

## 7. Contamination Firewall — Enforcement Mechanism

> Source: `debate/002-contamination-firewall/final-resolution.md`
> See also: `meta_spec.md` for content rules (MK-14 boundary contract)

### 7.1 Typed Schema with 4 Whitelist Categories (X38-D-04 → final-resolution.md §Decision 1)

`MetaLesson` typed schema with category enum enforcement. 4 F-06 whitelist
categories (permanent, no expansion in v1):

| Category | Coverage | Notes |
|----------|----------|-------|
| `PROVENANCE_AUDIT_SERIALIZATION` | ~25 rules | Single bucket for v1 (overload acknowledged, split deferred) |
| `ANTI_PATTERN` | ~23 rules | Methodology-level anti-patterns |
| `SPLIT_HYGIENE` | ~9 rules | Data split integrity |
| `STOP_DISCIPLINE` | ~3 rules | Kept as separate category (Facet C convergence) |

**Content gate**:
- Lesson with category outside whitelist → rejected
- Lesson with content tilting family/architecture/calibration-mode → rejected for
  mapped categories and genuine ambiguity
- Pure-gap structural priors (~10 Tier 2 rules) → permanent `UNMAPPED` governance
  tag + Tier 2 + SHADOW (Topic 004 MK-07 second fork)

**GAP/AMBIGUITY distinction** (permanent law):
- **GAP** (no category fits): `UNMAPPED` + Tier 2 + SHADOW. `UNMAPPED` is a
  governance tag (Topic 004), not a 5th content category. Does NOT retire in v1.
- **AMBIGUITY** (multiple categories fit): non-admissible pending human review
  (fail-closed)

### 7.2 State Machine Hash-Signing (X38-D-04 → final-resolution.md §Decision 2)

Each protocol stage transition signed by hash of existing artifacts:
- Contamination log only readable AFTER `frozen_spec.json` hash exists
- State machine prevents rollback (FROZEN → SCANNING is invalid transition)
- Hash-signing is core enforcement mechanism, not optional v1 complexity

### 7.3 Filesystem chmod (X38-D-04 → final-resolution.md §Decision 3)

chmod 444 after verdict is defense-in-depth guardrail, NOT primary enforcement.
Primary enforcement = typed schema (§7.1) + state machine (§7.2).

### 7.4 Cross-Spec Interface (MK-14)

Per Topic 004 MK-14: Topic 002 owns content gate (`ADMISSIBLE`/`BLOCKED`), Topic
004 owns lifecycle gate. `architecture_spec` exports `ContaminationCheck` API;
`meta_spec` exports `LessonSpec` schema. Both reference the MK-14 boundary contract.

---

## 8. Deployment Boundary

> Pending: Topic 011 (deployment boundary)

_Stub._

---

## 9. Convergence Analysis

> Pending: Topic 013 (convergence analysis)
> Cross-ref: §1.2 metric scopes (from Topic 001)

_Stub._

---

## 10. Bounded Recalibration Path

> Pending: Topic 016 (bounded recalibration)
> Cross-ref: §1.3 HANDOFF law (from Topic 001)

_Stub._

---

## 11. Epistemic Search Policy

> Pending: Topic 017 (epistemic search policy)
> Cross-ref: §9 convergence analysis (coverage metrics overlap), §7 firewall (reconstruction-risk gate), §1.2 metric scopes (V1 third scope stays narrow)
> Note: Topic 004 C3 (converged) established "Budget split = v2+ design. V1: all search is frontier." ESP builds on this foundation.

_Stub — to be filled after Topic 017 closure. Key sections:_
- _11.1 Intra-campaign illumination (cell-elite archive, descriptor tagging, epistemic_delta.json)_
- _11.2 CandidatePhenotype & StructuralPrior contracts (forbidden payload, reconstruction-risk gate)_
- _11.3 Inter-campaign promotion ladder (OBSERVED → REPLICATED_SHADOW → ACTIVE → DEFAULT_METHOD_RULE)_
- _11.4 Budget governor (coverage floor, exploit budget, contradiction resurrection)_
- _11.5 Framework evaluation criteria (acceptance test for ESP mechanism)_

---

## Traceability

| Section | Issue ID | Source |
|---------|----------|--------|
| §1.1 Campaign Definition | X38-D-03 | `debate/001-campaign-model/final-resolution.md` §Decision 1 |
| §1.2 Metric Scopes | X38-D-15 | `debate/001-campaign-model/final-resolution.md` §Decision 2 |
| §1.3 HANDOFF Law | X38-D-16 | `debate/001-campaign-model/final-resolution.md` §Judgment |
| §5.1 Philosophy Invariant | X38-D-01 | `debate/007-philosophy-mission/final-resolution.md` §Decision 1 |
| §5.2 3-Tier Claim Model | X38-D-20 | `debate/007-philosophy-mission/final-resolution.md` §Decision 2 |
| §5.3 Phase 1 Evidence Taxonomy | X38-D-22 | `debate/007-philosophy-mission/final-resolution.md` §Decision 3 |
| §5.4 Regime-Aware Policy Boundary | X38-D-25 | `debate/007-philosophy-mission/final-resolution.md` §Decision 4 |
| §7.1 Typed Schema + 4 Categories | X38-D-04 | `debate/002-contamination-firewall/final-resolution.md` §Decision 1 |
| §7.2 State Machine Hash-Signing | X38-D-04 | `debate/002-contamination-firewall/final-resolution.md` §Decision 2 |
| §7.3 Filesystem chmod | X38-D-04 | `debate/002-contamination-firewall/final-resolution.md` §Decision 3 |
| §7.4 Cross-Spec Interface (MK-14) | X38-D-04 / X38-MK-14 | `debate/002-contamination-firewall/final-resolution.md` + `debate/004-meta-knowledge/final-resolution.md` |
