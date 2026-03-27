# Architecture Spec — Draft

**Status**: DRAFT (seeded from Topic 001, 002, 004, 007, 008, 010 closures — 008 sections added 2026-03-27)
**Last updated**: 2026-03-27
**Dependencies**: 001(CLOSED) + 002(CLOSED) + 004(CLOSED) + 007(CLOSED) + 008(CLOSED) + 010(CLOSED) + 009 + 011 + 013 + 016 + 017
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

## 2. Identity Model & Provenance (Topic 008)

> Source: `debate/008-architecture-identity/final-resolution.md`

### 2.1 Three Pillars — v1 Architecture (X38-D-02 → final-resolution.md §Decision 1)

Three architectural pillars are sufficient for v1:

| Pillar | Responsibility | Lifecycle phase |
|--------|---------------|-----------------|
| **Contamination Firewall** | Typed schema + state machine + filesystem guardrail | Pre-campaign (what crosses campaign boundary) |
| **Protocol Engine** | 8-stage pipeline, phase gating, freeze checkpoint | Intra-campaign (how discovery runs) |
| **Meta-Updater** | Lesson lifecycle, 3-tier taxonomy, challenge/expiry | Post-campaign (what meta-knowledge survives) |

ESP (Epistemic Search Policy, Topic 017) is a Protocol Engine sub-component
governing search within Stages 3-6, not a 4th pillar. Responsibility mapping
(which pillar owns which obligation) is documentation, not an architectural
boundary. Revisiting the pillar count requires future evidence of an invariant
that no existing pillar can own without breaking another.

### 2.2 Protocol Version Identity (X38-D-13 → final-resolution.md §Decision 3)

`campaign.json` MUST declare a `protocol_version` field at creation time.

**Three identity axes** (adapted from gen4 evidence, offline-native):

| Axis | Alpha-Lab carrier | Changes when |
|------|-------------------|-------------|
| Protocol version | `protocol_version` in `campaign.json` | Protocol code or gating logic changes |
| Campaign lineage | `inherits_from` in `campaign.json` | New campaign opens (HANDOFF or new-data) |
| Session identity | Session directory + immutable artifacts | Each independent session within a campaign |

**Cross-protocol comparison rule**: Convergence analysis MUST flag when
comparing campaigns with different `protocol_version` values. Topic 001's
routing contract (`debate/001-campaign-model/final-resolution.md:121-143`)
enforces: if protocol identity changes AND results change → HANDOFF.

**Change-trigger taxonomy**: Deferred to Topics 003 (protocol content) and 015
(semantic change classification). What constitutes a version increment (major
vs minor vs no-increment) will be defined by those topics' change-impact
tables (`debate/015-artifact-versioning/findings-under-review.md:92-99`).

### 2.3 Candidate-Level Identity Contract (X38-SSE-04-IDV → final-resolution.md §Decision 4)

A candidate-level identity contract is a required architectural obligation,
sitting alongside (not inside) the macro provenance schema above.

**Structural pre-bucket fields** (declared by Topic 008):
- Descriptor hash
- Parameter family
- AST-hash subset

**Ownership split**:
- Topic 008: existence obligation + structural field list
- Topic 013: equivalence semantics (behavioral thresholds, hash granularity)
- Topic 017: consumption patterns (phenotype reconstruction-risk gate,
  cell-elite deduplication)

This contract serves Topic 010's deferred Scenario 1 (same-family
rediscovery) without overloading the macro provenance axes and satisfies
Topic 018's field 3 (`identity_vocabulary`) routing obligation.

---

## 3. Directory Structure (Topic 008)

> Source: `debate/008-architecture-identity/final-resolution.md` §Decision 2
> Confirmed tree: `docs/design_brief.md:150-167`

### 3.1 Target Layout (X38-D-09 → final-resolution.md §Decision 2)

```
/var/www/trading-bots/alpha-lab/
├── pyproject.toml              # uv project, separate venv
├── CLAUDE.md                   # AI context
├── README.md
│
├── src/alpha_lab/
│   ├── core/                   # types, data, engine, cost, metrics, audit
│   ├── features/               # registry, compute, threshold, signal, families/
│   ├── discovery/              # 8-stage protocol pipeline
│   ├── validation/             # wfo, bootstrap, plateau, ablation, regime, gates
│   ├── campaign/               # campaign, session, convergence, contamination, knowledge, oos
│   └── cli/                    # main, run_session, run_campaign, new_campaign, report
│
├── data/btcusdt/               # Data copies (SHA-256), NOT symlinks
│   ├── bars_2017_2026q1.csv
│   └── checksums.json
│
├── campaigns/                  # Campaign outputs (grow over time)
│   ├── c001_btc_2017_2026q1/
│   │   ├── campaign.json       # Protocol, data ref, status, inherits_from, protocol_version
│   │   ├── sessions/s001/...   # Per-session artifacts (immutable after verdict)
│   │   ├── convergence/        # Cross-session analysis
│   │   └── contamination.json  # Union contamination map
│   └── c002_btc_2017_2026q3/
│
├── knowledge/                  # Accumulated meta-knowledge (mutable)
│   ├── lessons.json
│   ├── lesson_history.json
│   └── campaigns_summary.json
│
└── tests/
    ├── unit/
    ├── integration/
    └── regression/
```

### 3.2 Design Principles

- **Code != Data != Results != Knowledge**: When the project grows, only
  `campaigns/` grows. Code, data snapshots, and knowledge are stable.
- **Separate venv**: Alpha-Lab uses its own virtualenv, not shared with
  `/var/www/trading-bots/.venv/`.
- **Data as copies**: Each campaign binds to an exact data snapshot via
  SHA-256 checksum. No symlinks (reproducibility via co-location).
- **`knowledge/` at root**: Mutable meta-knowledge state, not source code.
  Placed at root for visibility and independent versioning.

### 3.3 Campaign-to-Data Checksum Contract

`campaign.json` MUST carry an explicit checksum or manifest reference to its
bound data snapshot. The invariant is snapshot identity via SHA-256 — not a
particular storage topology. Whether the system uses shared snapshots with
manifest or per-campaign copies is an operational policy decision.

Source: `docs/design_brief.md:96-103,179-182`; `PLAN.md:445-447,581-599`.

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

> Source: `debate/010-clean-oos-certification/final-resolution.md`
> Cross-ref: §5.2 certification tier, §5.3 evidence taxonomy

### 6.1 Phase 2 Lifecycle (X38-D-12 → final-resolution.md §Decision 1)

Clean OOS is Phase 2 after research, not a campaign type:

```
Phase 1: RESEARCH (N campaigns HANDOFF, same data file)
  → winner chính thức or NO_ROBUST_IMPROVEMENT

Phase 2: CLEAN OOS (only if winner exists, wait for new data)
  Download new data → replay frozen winner on clean reserve
    ├── CLEAN_OOS_CONFIRMED → certification complete
    ├── CLEAN_OOS_INCONCLUSIVE → keep INTERNAL_ROBUST_CANDIDATE, re-trigger
    └── CLEAN_OOS_FAIL → Phase 3

Phase 3: NEW RESEARCH (only after FAIL, on expanded data)
  New campaign on full data (old + new), open search space
  → repeat Phase 1 → 2 → ...
```

**Clean reserve**: genuinely new data only (not internal holdout). Reserve
opened exactly once per attempt. Boundary: executable timestamp contract
(bar `close_time` per timeframe, not date string).

**CertificationVerdict schema**:
- `frozen_spec_ref`: path to frozen winner spec from research phase
- `reserve_boundary_h4`, `reserve_boundary_d1`: last bar `close_time` in
  research data (per timeframe)
- `reserve_end_h4`, `reserve_end_d1`: last bar `close_time` in reserve
- `append_data_ref`: path/hash of extended data file
- `verdict`: `CONFIRMED` | `INCONCLUSIVE` | `FAIL`
- `metrics`: evaluation results on reserve
- `iteration_count`: attempt number (1, 2, 3, ...)
- `previous_verdicts`: list of prior verdicts (for accumulation visibility)

**FAIL lineage**: immutable record in CertificationVerdict. Historical
evidence/provenance only — NOT anti-pattern, no MetaLesson pipeline
interaction.

**Module placement**: deferred to Topic 003 (pipeline structure).

### 6.2 Auto-Trigger Governance (X38-D-12/D-21 → final-resolution.md §Decision 2)

**Stateless predicate trigger**: `PENDING_CLEAN_OOS` fires whenever:
```
(winner exists) AND (elapsed since last_attempt_boundary > minimum_duration)
```

After `INCONCLUSIVE`, the Reserve Rollover Invariant sets
`last_attempt_boundary := reserve_end_*`, and the predicate re-evaluates
from that boundary.

**Governance per trigger**:
- Human researcher must act or explicitly defer with review date
- No silent indefinite deferral (violation)
- Enriched artifact: `iteration_count` + `previous_verdicts` (mandatory)
- Human researcher = escalation authority at every iteration
- No automatic count-based FAIL conversion (violates honest labeling)
- No universal cross-attempt escalation thresholds (V2+)

### 6.3 Verdict Taxonomy (X38-D-21 → final-resolution.md §Decision 3)

Three certification-tier verdicts:

| Verdict | Meaning | Next action |
|---------|---------|-------------|
| `CLEAN_OOS_CONFIRMED` | Winner validated by independent evidence | Certification complete |
| `CLEAN_OOS_INCONCLUSIVE` | Reserve underpowered; honest label | Maintain `INTERNAL_ROBUST_CANDIDATE`, wait, re-trigger |
| `CLEAN_OOS_FAIL` | Winner rejected by independent evidence | Phase 3: new research on expanded data |

**Reserve Rollover Invariant**: Attempt N+1 starts strictly after attempt N's
`reserve_end_*`. Prevents re-use of already-evaluated data across attempts.

### 6.4 Power Rules — Method-First (X38-D-24 → final-resolution.md §Decision 4)

Power rules are campaign-specific, predeclared before reserve opening.

**Mandatory minimum criteria**:
- Calendar-time coverage
- Trade count for statistical validity

**Additional dimensions** (method-dependent): regime coverage, exposure hours,
effect size thresholds. Determined by pre-registered power method per campaign.

**INCONCLUSIVE auto-path**: if predeclared power method says reserve is
underpowered → verdict is automatically `INCONCLUSIVE` before any metric
analysis.

No universal binding dimension set or numeric thresholds frozen in V1.

### 6.5 Pre-existing Candidate Treatment (X38-D-23 → final-resolution.md §Decision 5)

**Scenario 1 — Same-family rediscovery**: **Answered by Topic 008 (CLOSED
2026-03-27)**. Campaign lineage via `inherits_from` in `campaign.json`
(§2.2, D-13) provides the `program_lineage_id`-equivalent carrier.
Candidate-level structural identity via SSE-04-IDV (§2.3) provides the
same-family comparison contract. Topic 010 consumes both interfaces for
below-certification convergence signaling only. Clean OOS still required; no
automatic certification uplift.

**Scenario 2 — Contradiction**: Covered by Topic 007 semantic rule. If
same-archive search contradicts historical lineage, the artifact MUST surface
the contradiction explicitly below certification tier.

**Scenario 3 — NO_ROBUST_IMPROVEMENT + pre-existing candidate**: Derived
invariant. If shadow provenance contains a pre-existing candidate and the
campaign verdict is `NO_ROBUST_IMPROVEMENT`, that candidate remains unchanged
/ unadjudicated by x38, below certification tier. Not certification, not
contradiction, does not create a new x38 winner.

### 6.6 Cross-Topic Interfaces

| Interface | Owner | 010 provides/consumes |
|---|---|---|
| Pipeline integration (Phase 2 placement) | Topic 003 (F-05) | 010 provides: Phase 2 protocol; 003 consumes |
| Identity schema (same-family comparison) | Topic 008 (F-13) | 010 consumes: campaign lineage via `inherits_from` (D-13) + candidate-level identity via SSE-04-IDV for Scenario 1 |
| Recalibration/certification interaction | Topic 016 | 016 consumes: verdict taxonomy; defines re-certification rules |
| Power-floor methodology | Topic 017 (ESP-03) | 017 consumes: D-24 method-first contract |
| Contradiction semantic rule | Topic 007 (closed) | 010 consumes: MUST-surface rule for Scenario 2 |

---

## 7. Contamination Firewall — Enforcement Mechanism

> Source: `debate/002-contamination-firewall/final-resolution.md`
> See also: `meta_spec.md` for content rules (MK-14 boundary contract)

### 7.1 Typed Schema with 3 Whitelist Categories (X38-D-04 → final-resolution.md §Decision 1)

`MetaLesson` typed schema with category enum enforcement. 3 F-06 whitelist
categories (permanent, no expansion in v1):

| Category | Coverage | Notes |
|----------|----------|-------|
| `PROVENANCE_AUDIT_SERIALIZATION` | ~25 rules | Single bucket for v1 (overload acknowledged, split deferred per Facet B-Codex) |
| `ANTI_PATTERN` | ~26 rules | Methodology-level anti-patterns + absorbed `STOP_DISCIPLINE` (3 rules consolidated per Facet C convergence, Round 2) |
| `SPLIT_HYGIENE` | ~9 rules | Data split integrity |

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
| §6.1 Phase 2 Lifecycle | X38-D-12 | `debate/010-clean-oos-certification/final-resolution.md` §Decision 1 |
| §6.2 Auto-Trigger Governance | X38-D-12 / X38-D-21 | `debate/010-clean-oos-certification/final-resolution.md` §Decision 2 |
| §6.3 Verdict Taxonomy | X38-D-21 | `debate/010-clean-oos-certification/final-resolution.md` §Decision 3 |
| §6.4 Power Rules — Method-First | X38-D-24 | `debate/010-clean-oos-certification/final-resolution.md` §Decision 4 |
| §6.5 Pre-existing Candidate Treatment | X38-D-23 | `debate/010-clean-oos-certification/final-resolution.md` §Decision 5 |
| §6.6 Cross-Topic Interfaces | X38-D-12/D-21/D-23/D-24 | `debate/010-clean-oos-certification/final-resolution.md` §Cross-topic impact |
| §2.1 Three Pillars | X38-D-02 | `debate/008-architecture-identity/final-resolution.md` §Decision 1 |
| §2.2 Protocol Version Identity | X38-D-13 | `debate/008-architecture-identity/final-resolution.md` §Decision 3 |
| §2.3 Candidate-Level Identity | X38-SSE-04-IDV | `debate/008-architecture-identity/final-resolution.md` §Decision 4 |
| §3.1 Target Layout | X38-D-09 | `debate/008-architecture-identity/final-resolution.md` §Decision 2 |
| §3.3 Checksum Contract | X38-D-09 | `debate/008-architecture-identity/final-resolution.md` §Decision 2 |
