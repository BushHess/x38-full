# Architecture Spec — Draft

**Status**: DRAFT (seeded from Topic 001, 002, 004, 007, 008, 010, 013, 018 closures — §14 added 2026-03-31 from Topic 019)
**Last updated**: 2026-03-31
**Dependencies**: 001(CLOSED) + 002(CLOSED) + 004(CLOSED) + 007(CLOSED) + 008(CLOSED) + 010(CLOSED) + 013(CLOSED) + 009 + 011 + 016 + 017 + 019
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
├── data/                       # Symlinks or refs to data-pipeline output
│   └── data_manifest.json      # SHA-256 checksums + path mapping to source
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
- **Data from pipeline**: Each campaign binds to an exact data snapshot via
  SHA-256 checksum. Data lives at `/var/www/trading-bots/data-pipeline/output/`
  (parquet format, managed by data-pipeline). Research scope includes all 5
  data types (`spot_klines`, `futures_metrics`, `futures_fundingRate`,
  `futures_premiumIndexKlines`, `aggtrades_bulk`). Which data types a campaign
  uses is determined by research results, not pre-decided. `data_manifest.json`
  records checksums at campaign-creation time for reproducibility.
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

> Source: `debate/013-convergence-analysis/final-resolution.md`
> Cross-ref: §1.2 metric scopes (from Topic 001), §12.1 field 5 scan_phase_correction_method (from Topic 018)

### 9.1 Scan-Phase Correction Law (X38-SSE-09 -> final-resolution.md Decision 3)

**v1 operational default**: Holm (step-down) procedure at alpha_FWER = 0.05.

- **Holm alpha_FWER = 0.05**: Conservative family-wise error rate. One false discovery
  can redirect an entire cell's probe budget, so family-wise control is appropriate.
- **BH q_FDR = 0.10**: Documented upgrade path. Activated only after Topic 017 closes
  the required proof-consumption guarantee. Until then, BH is NOT a v1 default.
- **Provenance**: Fixed conventional v1 constants, not x38-derived calibration.

**Correction -> cell-elite ordering**: Correction precedes diversity preservation.
Holm filters at scan-phase entry (Stage 4); cell-elite diversity operates on
post-correction survivors within cells. Ordering: scan -> correct -> admit to cell ->
within-cell competition -> diversity preservation.

**Clarification**: alpha_FWER = 0.05 does NOT numerically "align" with per-test
alpha = 0.10 -- they are different error-control layers.

### 9.2 Equivalence Thresholds (X38-SSE-04-THR -> final-resolution.md Decision 4)

**Behavioral equivalence** (FROZEN):
- rho > 0.95 paired-return correlation cutoff (conventional v1 choice).
- Does NOT claim variance-decomposition justification.
- Placed above E5 cross-timescale rho ~ 0.92 (timescale variants should remain distinct).

**Structural hash granularity** (FROZEN, design-contract level):
- Minimum invariance surface: invariant with whitespace, comments, import order.
- Bucket by: structure of signal-generation logic (entry + exit) + sorted parameter
  schema (names + types).
- Exclude: parameter values from hash bucket.
- Behavioral audit handles cross-bucket functional equivalence.
- Compatible with Topic 008 (interface + structural pre-bucket fields, §2.3) and
  Topic 018 (AST-hash subset as hybrid method component, §12.1 field 3).
- Exact normalization algebra: implementation-defined for v1.

### 9.3 Robustness Bundle Minimum Requirements (SSE-04-THR items 3a/3b)

**Ownership** (FROZEN): Topic 013 owns "what 'minimum' means numerically."

**Exact numerics** (DEFERRED): structurally blocked by circular dependency with
Topic 017. 013 needs 017's consumption framework to set meaningful floors; 017
needs 013's production to set passing criteria.

Upstream input: Topic 018's working minimum inventory (5 proof components, 5 anomaly
axes) at judgment-call authority -- working handoff, not authoritative numeric law.

**Item 3b — Consumption sufficiency**: shared 013x017 surface. DEFERRED.

### 9.4 Anomaly Axis Thresholds (SSE-04-THR item 4)

**Methodology** (FROZEN): hybrid relative/absolute approach with sparsity guard for
small cell populations. Thresholds are relative to cell population but fall back to
absolute minimums below a population-size floor.

**Exact per-axis numerics** (DEFERRED): owned by Topic 017. Resolve in 013x017
integration.

### 9.5 Cross-Topic Interfaces

| Interface | Owner | 013 provides/consumes |
|---|---|---|
| Convergence-state + stall output | 013 (provides) | Consumed by 003 (stop logic), 010 (winner predicate), 001 (HANDOFF triggers) |
| Stop thresholds + ceiling | 013 (provides) | Consumed by 001 (bounded scope) |
| Scan-phase correction (field 5) | 013 (provides) | Consumed by 003 (breadth-activation gate) |
| Proof-consumption guarantee | 017 (provides) | 013 consumes: BH upgrade activation |
| Coverage floor -> stop interaction | 013x017 (noted) | Cross-topic tension, no action now |
| Feature family taxonomy | 006 (provides) | 013 consumes: hash pre-bucket compatibility (deferred) |

---

## 10. Bounded Recalibration Path

> Pending: Topic 016 (bounded recalibration)
> Cross-ref: §1.3 HANDOFF law (from Topic 001)

_Stub._

---

## 11. Epistemic Search Policy

> Pending: Topic 017 (epistemic search policy)
> Cross-ref: §9 convergence analysis (CLOSED — coverage metrics overlap, scan-phase correction), §7 firewall (reconstruction-risk gate), §1.2 metric scopes (V1 third scope stays narrow)
> Note: Topic 004 C3 (converged) established "Budget split = v2+ design. V1: all search is frontier." ESP builds on this foundation.

_Stub — to be filled after Topic 017 closure. Key sections:_
- _11.1 Intra-campaign illumination (cell-elite archive, descriptor tagging, epistemic_delta.json)_
- _11.2 CandidatePhenotype & StructuralPrior contracts (forbidden payload, reconstruction-risk gate)_
- _11.3 Inter-campaign promotion ladder (OBSERVED → REPLICATED_SHADOW → ACTIVE → DEFAULT_METHOD_RULE)_
- _11.4 Budget governor (coverage floor, exploit budget, contradiction resurrection)_
- _11.5 Framework evaluation criteria (acceptance test for ESP mechanism)_

---

## §12 Breadth-Expansion Contract (SSE-D-04)

> Seeded from Topic 018 closure (2026-03-27)
> Cross-ref: §2.3 candidate-level identity (008), §9 convergence analysis (013), §11 epistemic search policy (017)

_Stub — seeded from Topic 018 closure. Key content:_

### 12.1 7-Field Interface Contract

Protocol MUST declare all 7 interface fields before breadth activation:

1. `descriptor` — structural identity of the candidate
2. `comparison_domain` — which candidates compare against each other
3. `identity_vocabulary` — naming/hashing scheme (ownership: 008 interface + structural pre-bucket, 013 semantics, 017 consumption)
4. `equivalence_method` — how to determine if two candidates are "the same"
5. `scan_phase_correction_method` — multiplicity correction for breadth expansion (formula → 013)
6. `robustness_bundle` — which proof components are required
7. `invalidation_scope` — what gets invalidated when a field changes (details → 015)

Exact values for each field deferred to downstream topics. Protocol-level obligation: declare all 7, not leave any implicit.

### 12.2 Breadth-Activation Blocker

Breadth activation is blocked at `protocol_lock` until all 7 fields are declared. This is a hard gate — no implicit defaults, no partial declarations.

**Trace**: SSE-D-04 → `debate/018-search-space-expansion/final-resolution.md` Decision 3

---

## §13 Discovery Pipeline Routing (SSE-D-01)

> Seeded from Topic 018 closure (2026-03-27)
> Cross-ref: all discovery-related sections in this spec and other specs

_Stub — seeded from Topic 018 closure. Key content:_

### 13.1 No Topic 018 Umbrella

Topic 018 does not own any substance. All discovery mechanisms are distributed to existing topics:

| Mechanism | Owner topic | Routing issue |
|-----------|-----------|---------------|
| Generation modes (grammar, registry) | 006 (feature engine) | SSE-D-03 |
| 3-layer lineage + contradiction storage | 015 (artifact versioning) | SSE-D-07, SSE-D-08 |
| Recognition topology + proof inventory | 017 (epistemic search) | SSE-D-05, SSE-D-08-CON |
| Multiplicity correction | 013 (convergence analysis) | SSE-D-09 |
| Identity vocabulary | 008 (architecture identity) | SSE-D-04 field 3 |
| Breadth-activation gate | 003 (protocol engine) | SSE-D-04 |

### 13.2 Governance

New discovery topic only if downstream closure reports reveal an explicit unresolved gap. Existing routing confirmed by standard 2-agent debate (2026-03-27).

**Trace**: SSE-D-01 → `debate/018-search-space-expansion/final-resolution.md` Decision 1

---

## §14 Discovery Loop Architecture (Topic 019 — PENDING DEBATE)

> **Authority**: This section is a PROPOSAL from Topic 019 (OPEN, 2026-03-29).
> NOT authoritative until debate closure. May be modified, simplified, or rejected.

> **Motivation**: v1 architecture (§2.1, Three Pillars) provides a validation
> factory — search + validate within declared space. But 100% of btc-spot-dev
> alpha came from human intuition outside the framework (DFL-01). §14 adds an
> R&D lab — a human-AI collaborative discovery loop that is the 4th architectural
> component alongside the 3 pillars.

### 14.1 Relationship to Three Pillars

The v1 Three Pillars (§2.1) are DEFENSIVE — prevent contamination, enforce
process, record methodology. They ensure research is HONEST but do not help
research be PRODUCTIVE. The Discovery Loop is GENERATIVE — it enables the
creation of new feature concepts that the Three Pillars then validate.

| Component | Role | Phase | Lifecycle |
|-----------|------|-------|-----------|
| **Contamination Firewall** (Pillar 1) | Prevent data leakage | Pre-campaign | Defensive |
| **Protocol Engine** (Pillar 2) | Enforce discovery process | Intra-campaign | Defensive |
| **Meta-Updater** (Pillar 3) | Record methodology lessons | Post-campaign | Defensive |
| **Discovery Loop** (New) | Enable human-AI feature invention | Cross-campaign | Generative |

The Discovery Loop is NOT a 4th pillar. Revisiting pillar count requires
evidence of an invariant that no existing pillar can own (§2.1). The Discovery
Loop is a CROSS-CUTTING component that interacts with all 3 pillars:

- Uses Contamination Firewall: DFL-04 contamination model classifies every
  information flow in the loop
- Uses Protocol Engine: DFL-10 Stage 2.5 inserts into pipeline; DFL-08
  Stage 5 feeds into normal validation
- Uses Meta-Updater: Discovery findings become meta-knowledge if they
  survive campaigns (MK-17 shadow → promotion ladder per 017)

### 14.2 Components

The Discovery Loop consists of 6 sub-components, each defined in
`drafts/discovery_spec.md` §6-§11:

| Component | Spec Section | Purpose |
|-----------|-------------|---------|
| Data Profiling Layer | §6 | Characterize raw data BEFORE grammar design |
| Grammar Depth-2+ | §7 | Compose features from building blocks |
| Information-Theoretic Pre-Filter | §8 | Screen features without consuming budget |
| Statistical Budget Tracker | §9 | Account for finite validation capacity |
| Human-AI Collaboration Loop | §10 | Structured discovery through deliberation |
| Feature Graduation Pipeline | §11 | End-to-end path from pattern to registry |

### 14.3 Information Flow

Two parallel discovery paths, converging at validation:

```
                    ┌──────────────────────────┐
                    │     RAW DATA             │
                    │   (13 fields, 4 TFs)     │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │  §6 DATA PROFILING       │ ← Pipeline (Stage 2.5)
                    │  data_profile.json       │
                    └────────────┬─────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                   │
   PATH A: GRAMMAR         PATH B: HUMAN-AI COLLABORATION
              │                  │                   │
    ┌─────────▼────────┐  ┌─────▼──────┐  ┌────────▼────────┐
    │  §1+§7 GRAMMAR   │  │ §10 AI     │  │  §10 HUMAN      │
    │  DEPTH-2 SCAN    │  │ ANALYSIS   │  │  INSIGHT        │
    │  [OHLCV-only]    │  │ LAYER      │  │  (domain        │
    │  ~140K features  │  │ [all data] │  │   knowledge)    │
    └─────────┬────────┘  └─────┬──────┘  └────────┬────────┘
              │                  │                   │
    ┌─────────▼────────┐  ┌─────▼──────────────▼────┐
    │  §8 MI PRE-FILTER│  │ HUMAN REVIEW             │
    │  Top-200 by rank │  │ (Tier 3 authority)       │
    │  [reduces 140K   │  │ TEMPLATE / GRAMMAR /     │
    │   to ~200]       │  │ INVESTIGATE / DISCARD    │
    └─────────┬────────┘  └──────────┬───────────────┘
              │                      │
              │           ┌──────────▼───────────────┐
              │           │ §10.5 DELIBERATION-GATED │
              │           │ CODE (if novel code       │
              │           │ needed for human template)│
              │           └──────────┬───────────────┘
              │                      │
    ┌─────────▼──────────┐  ┌────────▼───────────────┐
    │ HUMAN REVIEW       │  │ Strategy implementation │
    │ of MI survivors    │  │ (template or novel code)│
    │ (~200 → ~3-10)    │  │                         │
    └─────────┬──────────┘  └────────┬───────────────┘
              │                      │
              └──────────┬───────────┘
                         │
    ┌────────────────────▼──────────────────────────┐
    │  §9 BUDGET CHECK                              │
    │  k_tested < budget? → proceed                 │
    │  k_tested ≥ budget? → WARN, human override    │
    └────────────────────┬──────────────────────────┘
                         │
    ┌────────────────────▼──────────────────────────┐
    │  VALIDATION PIPELINE (existing, all 7 gates)  │
    │  [Budget cost: 1 UNIT per feature]            │
    └────────────────────┬──────────────────────────┘
                         │
                PROMOTE / HOLD / REJECT
```

**Path A** (grammar): automated generation → MI ranking → human review → validation.
Pre-filter applies. Human-originated templates do NOT go through MI pre-filter.

**Path B** (human-AI): AI analysis + human insight → deliberation → code → validation.
Human judgment IS the filter. No MI screening needed.

### 14.4 Key Design Properties

| Property | Value | Rationale |
|----------|-------|-----------|
| Human always in loop | AI proposes, human decides | Statistical budget requires small K → human filters |
| Results-aware analysis | AI analysis layer sees everything | Discovery requires pattern detection in results |
| Results-blind grammar | Automated enumeration stays OHLCV-only | Prevent combinatorial explosion in search |
| Budget-conscious | Every formal test tracked | N=188, WFO N=8 folds → K_max empirical (possibly 1-3 under WFO) |
| Provenance end-to-end | Every feature traceable to origin | Contamination firewall integration |
| Not a 4th pillar | Cross-cutting component | Interacts with all 3 pillars without replacing them |

### 14.5 Capacity Estimate (btc-spot-dev specific)

| Parameter | Value |
|-----------|-------|
| Available trades | ~188 |
| WFO folds | 8 (binding constraint on power) |
| Grammar depth-2 candidates (OHLCV) | ~140,000 |
| After MI pre-filter (top-200) | ~200 |
| After human review | ~3-10 |
| After full validation | unknown — depends on power |

**Binding constraint**: WFO Wilcoxon with 8 folds has power < 50% at α=0.05
for a single test with Δ_Sharpe = 0.30. This means the budget is VERY tight
under the current validation pipeline — possibly K_max ≈ 1-3.

**This is the same problem as E5-ema21D1**: WFO p=0.125 > α=0.10, verdict
HOLD. The algorithm works but the test cannot confirm it.

**Implication**: v2's discovery capacity is gated by validation power, not by
discovery technology. Either (a) WFO reform increases power (more folds, longer
data), (b) trade-level tests supplement WFO, or (c) accept that few features
can be formally validated from current data. The exact K_max requires a power
simulation study — it cannot be determined from spec alone.

### 14.6 Module Placement in Directory Structure

Extends §3.1 target layout with 2 new package areas. Exact module boundaries
are implementation decisions — the names below are ILLUSTRATIVE, not prescribed.

```
src/alpha_lab/
├── discovery/              # Extended with v2 capabilities
│   ├── ...                 # Existing 8-stage pipeline modules
│   ├── [data profiling]    # §6 — Stage 2.5 characterization
│   ├── [grammar v2]        # §7 — depth-2 composition engine
│   ├── [MI pre-filter]     # §8 — information-theoretic screening
│   ├── [budget tracker]    # §9 — statistical budget accounting
│   └── [graduation]        # §11 — 5-stage feature graduation
├── analysis/               # NEW package — AI analysis layer (§10)
│   ├── [result analysis]   # Result-domain pattern detection
│   ├── [data analysis]     # Data-domain pattern detection
│   └── [report generation] # DiscoveryReport (DFL-02 contract)
```

**Note**: `src/alpha_lab/` does not exist yet. All directory structure is
from the §3.1 target layout. Module names will be decided during alpha-lab
implementation, not by this spec.

### 14.7 Cross-Section Interfaces

| Interface | Provider | Consumer |
|-----------|----------|----------|
| `data_profile.json` | §6 → pipeline Stage 2.5 | §7 grammar design, §10 AI analysis |
| Grammar depth-2 features | §7 → feature engine (006) | §8 pre-filter |
| MI-screened candidates | §8 → graduation pipeline | §11 Stage 1 |
| Budget state | §9 → budget tracker | §11 Stage 5 (check before validation) |
| DiscoveryReport | §10 → AI analysis layer | §11 Stage 2-3 (human review) |
| Feature registry entry | §11 → graduation Stage 4 | F-08 (006) registry |
| Contamination class | DFL-04 → every stage | §7 firewall (002) |

**Trace**: DFL-01 through DFL-12 → `debate/019-discovery-feedback-loop/findings-under-review.md`

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
| §12.1 7-Field Interface Contract | SSE-D-04 | `debate/018-search-space-expansion/final-resolution.md` Decision 3 |
| §12.2 Breadth-Activation Blocker | SSE-D-04 | `debate/018-search-space-expansion/final-resolution.md` Decision 3 |
| §9.1 Scan-Phase Correction Law | X38-SSE-09 | `debate/013-convergence-analysis/final-resolution.md` Decision 3 |
| §9.2 Equivalence Thresholds | X38-SSE-04-THR | `debate/013-convergence-analysis/final-resolution.md` Decision 4 |
| §9.3 Robustness Bundle Minimums | X38-SSE-04-THR | `debate/013-convergence-analysis/final-resolution.md` Decision 4 |
| §9.4 Anomaly Axis Thresholds | X38-SSE-04-THR | `debate/013-convergence-analysis/final-resolution.md` Decision 4 |
| §9.5 Cross-Topic Interfaces | X38-CA-01/CA-02/SSE-09/SSE-04-THR | `debate/013-convergence-analysis/final-resolution.md` |
| §13.1 Discovery Pipeline Routing | SSE-D-01 | `debate/018-search-space-expansion/final-resolution.md` Decision 1 |
| §14.1 Relationship to Pillars | DFL-01 | `debate/019-discovery-feedback-loop/findings-under-review.md` (PENDING) |
| §14.2 Components | DFL-01–DFL-12 | `debate/019-discovery-feedback-loop/findings-under-review.md` (PENDING) |
| §14.3 Information Flow | DFL-01–DFL-12 | `debate/019-discovery-feedback-loop/findings-under-review.md` (PENDING) |
| §14.5 Capacity Estimate | DFL-11 | `debate/019-discovery-feedback-loop/findings-under-review.md` (PENDING) |
| §14.6 Module Placement | DFL-01–DFL-12 | `debate/019-discovery-feedback-loop/findings-under-review.md` (PENDING) |
