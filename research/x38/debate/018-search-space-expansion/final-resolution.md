# Final Resolution — Search-Space Expansion

**Topic ID**: X38-T-18
**Closed**: 2026-03-27
**Rounds**: 6
**Participants**: claude_code, codex
**Prior debate**: 4-agent extra-canonical (7 rounds, input evidence only)

---

## Decisions

| Issue ID | Finding | Resolution | Type | Round closed |
|----------|---------|------------|------|-------------|
| SSE-D-01 | Pre-lock generation lane ownership | Accepted | Converged | 2 |
| SSE-D-02 | Bounded ideation (4 hard rules) | Accepted | Converged | 2 |
| SSE-D-03 | Grammar depth-1 seed + conditional registry_only | Accepted | Converged | 2 |
| SSE-D-04 | 7-field breadth-activation contract | Accepted | Converged | 2 |
| SSE-D-05 | Recognition stack: pre-freeze topology + named working minimum inventory | Modified (Judgment call) | Judgment call | 6 |
| SSE-D-06 | Hybrid equivalence (structural + behavioral, no LLM) | Accepted | Converged | 2 |
| SSE-D-07 | 3-layer lineage semantic split | Accepted (routed → 015) | Converged | 2 |
| SSE-D-08 | Contradiction registry: shadow-only, storage → 015, consumption → 017 | Accepted (routed → 015/017) | Converged | 2 |
| SSE-D-09 | Multiplicity control coupling via SSE-D-04 field 5 | Accepted (routed → 013) | Converged | 2 |
| SSE-D-10 | Domain-seed = optional provenance hook, no replay | Accepted | Converged | 2 |
| SSE-D-11 | APE v1 = template parameterization only | Accepted | Converged | 2 |

---

## Key design decisions (for drafts/)

### Decision 1: Lane ownership fold (SSE-D-01)

**Accepted position**: Discovery mechanisms fold into 6 existing topics
(006/015/017/013/008/003). No Topic 018 umbrella for substance — topic exists
only as a debate registry entry for the synthesis artifact. Ownership split with
explicit object boundaries. New topic only if downstream closure reports reveal
an explicit unresolved gap.

**Rejected alternative**: Create a dedicated Topic 018 to own all discovery
substance, with downstream topics receiving delegated scope.

**Rationale**: The folding argument (originally from ChatGPT Pro R1 in the
extra-canonical debate, re-confirmed by both agents in standard debate R1-R2)
holds: each discovery mechanism maps cleanly to an existing topic's scope.
Routing table is unnecessary because `x38_RULES.md:84-94` already governs
downstream authority, and each downstream topic's `findings-under-review.md`
carries the routed issues. See `claude_code/round-1_opening-critique.md` §SSE-D-01
(ACCEPT with amendment), `codex/round-1_rebuttal.md` §SSE-D-01 (concurs on
existing ledgers sufficiency). Converged R2.

---

### Decision 2: Bounded ideation rules + cold-start activation (SSE-D-02/03)

**Accepted position**: Bounded ideation replaces SSS (Structured Search Space)
with 4 hard rules:
1. **Results-blind** — ideation sees NO results from any session
2. **Compile-only** — output must compile (syntactically valid strategy spec)
3. **OHLCV-only** — only OHLCV + volume data as input
4. **Provenance-tracked** — every generated candidate records its generation method

Two generation modes at protocol lock:
- `grammar_depth1_seed` (mandatory default) — deterministic grammar enumeration
  producing depth-1 seeds from declared building blocks
- `registry_only` (conditional) — activated when registry is non-empty AND frozen
  AND `grammar_hash`-compatible (3 conditions, not 2)

Cold-start activation: `grammar_depth1_seed` is always available. `registry_only`
requires all 3 guards satisfied.

**Rejected alternative**: SSS (Structured Search Space) — reproduces discovery
origins like VDO. Rejected because seeing registry results creates contamination
risk that outweighs origin-story value.

**Rationale**: Contamination risk from seeing registry > origin story value.
Grammar-provenance admissibility policing belongs in Topics 002/004 (firewall),
not in D-02's lane-input contract. See `claude_code/round-1_opening-critique.md`
§SSE-D-02/03, `codex/round-1_rebuttal.md` §SSE-D-02 (grammar-provenance →
002/004), `codex/round-1_rebuttal.md` §SSE-D-03 (3-condition guard).
`codex/round-2_reviewer-reply.md` §7(c) confirmation. Converged R2.

---

### Decision 3: Breadth-expansion 7-field interface contract (SSE-D-04)

**Accepted position**: Protocol MUST declare all 7 interface fields before
breadth activation. Fields:
1. `descriptor` — what the candidate looks like (structural identity)
2. `comparison_domain` — which candidates compare against each other
3. `identity_vocabulary` — how to name/hash candidates (ownership: 008 interface
   + structural pre-bucket, 013 semantics, 017 consumption — per Topic 008
   Decision 4, SSE-04-IDV)
4. `equivalence_method` — how to determine if two candidates are "the same"
5. `scan_phase_correction_method` — multiplicity correction for breadth expansion
6. `robustness_bundle` — which proof components required
7. `invalidation_scope` — what gets invalidated when a field changes

Exact values for each field deferred to downstream topics. Protocol-level
obligation: declare all 7, not leave any implicit.

**Rejected alternative**: Fewer fields (e.g., 4-5) with implicit defaults for
missing concerns. Rejected because implicit defaults create governance gaps
that surface only at integration time.

**Rationale**: Topic 008 closure (2026-03-27) resolved the field 3 owner split
authoritatively via Decision 4 (SSE-04-IDV). See `claude_code/round-1_opening-critique.md`
§SSE-D-04 (field 3 owner gap), `codex/round-1_rebuttal.md` §SSE-D-04 (Topic 008
resolves it), `claude_code/round-2_author-reply.md` §SSE-D-04 (concedes 008
Decision 4 is authoritative). Converged R2 with full 7-field reconciliation
in `codex/round-2_reviewer-reply.md`.

---

### Decision 4: Surprise lane recognition topology + working minimum inventory (SSE-D-05)

**Accepted position (Modified — Judgment call)**:

Topic 018 adopts a working minimum inventory for handoff:

**Pre-freeze recognition topology**:
`surprise_queue → equivalence_audit → proof_bundle → freeze`

Topology stops at freeze — does NOT include post-freeze extensions
(`freeze_comparison_set → candidate_phenotype → contradiction_registry`).
Post-freeze stages scoped to downstream topics (017, 003, 015).

**Working minimum inventory** (Judgment call authority):
- 5 anomaly axes: `decorrelation_outlier`, `plateau_width_champion`,
  `cost_stability`, `cross_resolution_consistency`, `contradiction_resurrection`
- 5 proof components: `nearest_rival_audit`, `plateau_stability_extract`,
  `cost_sensitivity_test`, `dependency_stressor`, `contradiction_profile`
- Proof item 4: family-level name = `dependency_stressor`;
  `ablation_or_perturbation_test` is valid alias/concrete form
- NOT described as immutable historically-converged exact label set
- Thresholds and proof-consumption rules: 017/013 own
- Expansion beyond this minimum: requires explicit downstream finding

**Rejected alternative (Reviewer position)**: Narrower mechanism — pre-freeze
topology + required 5+5 family cardinality without exact naming. Exact naming
not cleanly settled by authoritative record due to material label drift in
archive evidence.

**Rejected alternative (Author overreach, corrected R6)**: Topology extending
past freeze (post-freeze chain), authority narrowing ("do not add, remove, or
replace" instead of "minimum"), and overclaimed archive provenance ("11 rounds,
zero challenges"). All three corrections applied per `codex/round-5_reviewer-reply.md`.

**Human Researcher Judgment (BINDING)**:

> Type: Judgment call (Round 6)
> Decision: Hybrid — Reviewer correct on status (Judgment call, not
> Converged); Author correct on handoff value (named working minimum
> inventory needed for downstream consumption).
>
> NOTE (Judgment call, round 6): Authoritative evidence locks pre-freeze
> recognition topology and minimum 5+5 floor, but does not cleanly lock
> a single exact label set without drift. However, downstream Topics
> 017/013 need named objects to write thresholds and proof-consumption
> semantics.
>
> Lựa chọn: Topic 018 adopts a working minimum inventory for handoff:
> - Pre-freeze recognition topology:
>   surprise_queue → equivalence_audit → proof_bundle → freeze
> - 5 anomaly axes: decorrelation_outlier, plateau_width_champion,
>   cost_stability, cross_resolution_consistency, contradiction_resurrection
> - 5 proof components: nearest_rival_audit, plateau_stability_extract,
>   cost_sensitivity_test, dependency_stressor, contradiction_profile
> - Proof item 4: family-level name = dependency_stressor;
>   ablation_or_perturbation_test is valid alias/concrete form
> - NOT described as immutable historically-converged exact label set
> - Topology stops at freeze — does NOT include post-freeze extensions
>   (freeze_comparison_set → candidate_phenotype → contradiction_registry)
> - Thresholds and proof-consumption rules: 017/013 own
> - Expansion beyond this minimum: requires explicit downstream finding
>
> Lý do: Archive evidence shows material label drift (4→5 dimensions,
> component 4 naming inconsistency, ChatGPT Pro deferred exact taxonomy
> downstream). Pure Converged overstates convergence. Pure unnamed family
> is operationally too weak for 017/013 handoff. Hybrid gives named
> working minimum at Judgment call authority level.
>
> Decision owner: human researcher

**Rationale**: The debate narrowed from broad disagreement to a precise boundary
question: count-level vs named inventory. Archive evidence shows label drift
(Claude R3 used 4 dimensions with "risk-profile", later replaced; ChatGPT Pro
R5 deferred exact taxonomy; Codex R4/R6 used "dependency stressor" generically
vs exact `ablation_or_perturbation_test`). Pure Converged overstates what the
record supports. Pure unnamed family is operationally too weak for 017/013
handoff (Topic 017 `findings-under-review.md:426-435` presupposes named objects
for per-axis thresholds).

See: `claude_code/round-3_author-reply.md` (locks 5+5 named list),
`codex/round-3_reviewer-reply.md` (rejects: non-authoritative source),
`claude_code/round-4_author-reply.md` (withdraws, defers to closure),
`codex/round-4_reviewer-reply.md` (count-only vs named),
`claude_code/round-5_author-reply.md` (restores named from debate record),
`codex/round-5_reviewer-reply.md` (three overreaches identified),
`claude_code/round-6_author-reply.md` (corrections applied),
`codex/round-6_reviewer-reply.md` (final Judgment call recommendation).

---

### Decision 5: Hybrid equivalence method (SSE-D-06)

**Accepted position**: Deterministic hybrid equivalence:
1. **Structural pre-bucket** — descriptor hash, parameter family, AST-hash
   subset → fast deterministic grouping
2. **Behavioral nearest-rival audit** — compare performance profiles of
   structurally-similar candidates → detect functional equivalence despite
   structural differences

No LLM judge. Versioned determinism: thresholds are part of the equivalence
definition and must be versioned. Thresholds/invalidation details deferred
downstream.

**Rejected alternative**: AST-hash only (Gemini's position in extra-canonical
debate, withdrawn R6). Pure structural matching misses functional equivalence
(two structurally different strategies that behave identically).

**Rationale**: Hybrid preserves determinism while catching functional equivalence.
Topic 008 Decision 4 (SSE-04-IDV) established the ownership split: 008 owns
interface + structural pre-bucket fields, 013 owns semantics, 017 owns
consumption. See `claude_code/round-1_opening-critique.md` §SSE-D-06,
`codex/round-1_rebuttal.md` §SSE-D-06 (versioned determinism),
`codex/round-2_reviewer-reply.md` §7(c) confirmation. Converged R2.

---

### Decision 6: 3-layer lineage semantic split (SSE-D-07, routed → 015)

**Accepted position**: Lineage split into 3 semantic layers:
1. `feature_lineage` — tracks feature provenance (where did this indicator come from)
2. `candidate_genealogy` — tracks candidate evolution (parent→child relationships)
3. `proposal_provenance` — tracks how a candidate was proposed (grammar, template, human)

Field enumeration and invalidation matrix deferred to Topic 015 (X38-SSE-07).

**Rejected alternative**: Single flat lineage record. Rejected because different
consumers need different lineage facets (firewall needs provenance, convergence
analysis needs genealogy, feature engine needs feature lineage).

**Rationale**: Semantic split maps cleanly to consumer needs. See
`claude_code/round-1_opening-critique.md` §SSE-D-07,
`codex/round-1_rebuttal.md` §SSE-D-07 (concurs, confirms routing).
Converged R2.

---

### Decision 7: Contradiction memory — shadow-only (SSE-D-08, routed → 015/017)

**Accepted position**: Contradiction registry operates at descriptor level,
shadow-only (MK-17 ceiling from Topic 004). Storage contract → Topic 015
(X38-SSE-08). Consumption semantics → Topic 017 (X38-SSE-08-CON).

Queue-priority carveout scope classification (whether contradiction resurrection
gets ORDER_ONLY or different priority in surprise queue) is an unresolved 017
question, not a 018 decision.

**Rejected alternative**: Active contradiction registry that can influence
candidate selection. Rejected because MK-17 (same-dataset priors = shadow-only)
is a settled Topic 004 invariant.

**Rationale**: MK-17 ceiling is binding. Shadow-only means contradictions are
recorded and surfaced but cannot directly block or promote candidates. See
`claude_code/round-1_opening-critique.md` §SSE-D-08 (queue-priority probe),
`codex/round-1_rebuttal.md` §SSE-D-08 (017 treats ORDER_ONLY as active scope),
`claude_code/round-2_author-reply.md` §SSE-D-08 (concedes scope is 017 question).
Converged R2.

---

### Decision 8: Multiplicity control coupling (SSE-D-09, routed → 013)

**Accepted position**: Breadth expansion creates a multiple-testing problem.
Multiplicity control is coupled to SSE-D-04 field 5
(`scan_phase_correction_method`). The exact correction formula is deferred to
Topic 013 (X38-SSE-09). Invalidation mechanics deferred to Topic 015.

**Rejected alternative**: Multiplicity correction as a standalone concern
independent of the breadth-activation contract. Rejected because correction
must be aware of how many candidates were expanded (field 5 provides this).

**Rationale**: Coupling ensures the correction method knows the expansion scope.
See `claude_code/round-1_opening-critique.md` §SSE-D-09 (concurs with routing),
`codex/round-1_rebuttal.md` §SSE-D-09 (confirms coupling).
`codex/round-2_reviewer-reply.md` §7(c) confirmation. Converged R2.

---

### Decision 9: Domain-seed hook provenance (SSE-D-10)

**Accepted position**: Domain-seed is an optional provenance hook only. No replay
semantics, no session format, no catalog infrastructure. Composition provenance
preserved via lineage (SSE-D-07).

**Rejected alternative**: Domain-seed as a full replay mechanism that imports
online authoring patterns (session format, catalog). Rejected per
`docs/online_vs_offline.md:71-82`: replay machinery imports online authoring
without source-backed need for the offline paradigm.

**Rationale**: The offline paradigm (Alpha-Lab) does not need session replay.
Provenance is preserved through lineage tracking, not through replay capability.
See `claude_code/round-1_opening-critique.md` §SSE-D-10,
`codex/round-1_rebuttal.md` §SSE-D-10 (replay = online import).
Converged R2.

---

### Decision 10: APE v1 scope boundary (SSE-D-11)

**Accepted position**: APE (Automated Parameter Exploration) v1 = template
parameterization only. No free-form code generation. Correctness guarantee is
absent in v1 (no verification mechanism exists yet), so generation is limited
to filling declared template parameters with values from declared ranges.

Free-form code generation is a v2+ capability, gated on a verification mechanism
being designed and validated.

**Rejected alternative**: APE v1 includes bounded code generation (e.g.,
indicator composition). Rejected because arbitrary code bypasses the current
validation/firewall model — there is no compile-time or runtime verification
that generated code is correct.

**Rationale**: Parameterization-only is the correct v1 scope because it preserves
the compile-only and provenance-tracked hard rules from SSE-D-02. See
`claude_code/round-1_opening-critique.md` §SSE-D-11,
`codex/round-1_rebuttal.md` §SSE-D-11 (bounded auditable generation only).
`codex/round-2_reviewer-reply.md` §7(c) confirmation. Converged R2.

---

## Unresolved tradeoffs (for human review)

- **SSE-D-05**: Exact label set stability — named inventory adopted at Judgment
  call authority, not Converged. Future label changes require explicit downstream
  finding. Archive evidence shows material drift (4→5 dimensions, component 4
  naming inconsistency). The working minimum inventory is operationally sufficient
  for 017/013 handoff but should not be treated as immutable.

- No other unresolved tradeoffs remain. All 10 other issues reached Converged
  with complete steel-man exchanges.

---

## Cross-topic impact

| Downstream topic | Routed from | Impact |
|------------------|-------------|--------|
| 006 (feature engine) | SSE-D-03 | `generation_mode` feeds registry acceptance — registry must accept auto-generated features from `grammar_depth1_seed` |
| 015 (artifact versioning) | SSE-D-07, SSE-D-08 | 3-layer lineage (X38-SSE-07) + contradiction storage (X38-SSE-08) + identity vocabulary invalidation (X38-SSE-04-INV) |
| 017 (epistemic search) | SSE-D-05, SSE-D-08-CON | Recognition topology + named inventory for thresholds (SSE-D-05) + contradiction consumption semantics (X38-SSE-08-CON) + cell equivalence (X38-SSE-04-CELL) |
| 013 (convergence analysis) | SSE-D-09 | Multiplicity correction formula via SSE-D-04 field 5 (X38-SSE-09) + thresholds (X38-SSE-04-THR) |
| 008 (architecture identity) | SSE-D-04 field 3 | `identity_vocabulary` routing — resolved via Topic 008 Decision 4 (SSE-04-IDV). Topic 008 already CLOSED. |
| 003 (protocol engine) | SSE-D-04 | Breadth-activation blocker at `protocol_lock` — protocol must declare all 7 fields before activation. Stage 3 scan-phase multiple-testing routed via SSE-D-09→013. |

---

## Draft impact

| Draft | Sections affected | Action needed |
|-------|------------------|---------------|
| `discovery_spec.md` | §1 Bounded ideation, §2 Recognition stack, §3 APE v1, §4 Domain-seed hook, §5 Hybrid equivalence | Create (new spec) |
| `architecture_spec.md` | §12 Breadth-expansion contract, §13 Discovery pipeline routing | Seed new sections |

---

## Evidence sources

- **Standard debate**: 12 round files (`claude_code/round-{1-6}*.md` + `codex/round-{1-6}*.md`)
- **Extra-canonical archive**: `docs/search-space-expansion/debate/` (4 proposals + 4×7 rounds, input evidence only)
- **Cross-topic evidence**: Topic 008 `final-resolution.md` (SSE-04-IDV), Topic 004 `final-resolution.md` (MK-17), Topic 017 `findings-under-review.md` (per-axis thresholds presuppose named objects)
- **Codex closure audit**: `codex/judgment-call-memo.md` (2026-03-27, standard 2-agent debate)
