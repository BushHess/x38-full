# Final Resolution — Architecture Pillars & Identity

**Topic ID**: X38-T-08
**Closed**: 2026-03-27
**Rounds**: 4 (author) / 4 (reviewer)
**Participants**: claude_code, codex

## Decisions

| Issue ID | Finding | Resolution | Type | Round closed |
|----------|---------|------------|------|-------------|
| X38-D-02 | Three pillars sufficiency | Accepted — 3 pillars sufficient for v1; responsibility map is documentation only | Converged | 2 |
| X38-D-09 | Directory structure | Modified — tree stands, tighten campaign-to-data checksum/manifest contract in `campaign.json` | Converged | 2 |
| X38-D-13 | Three-identity-axis model | Modified — add explicit `protocol_version` in `campaign.json`; defer bump taxonomy to 003/015 | Converged | 2 |
| X38-SSE-04-IDV | Candidate-level identity vocabulary | Accepted — required contract alongside D-13 (not 4th macro axis); 008 interface, 013 semantics, 017 consumption | Converged | 2 |

All four issues converged via full §7 process: §7(a)+(b) in
`claude_code/round-2_author-reply.md`, §7(c) confirmation in
`codex/round-2_reviewer-reply.md`. No steel-man was rejected or required retry.

---

## Round symmetry (rules.md §14b)

Author (claude_code): 4 rounds (R1 opening-critique, R2 author-reply, R3
author-reply, R4 author-reply).
Reviewer (codex): 4 rounds (R1 rebuttal, R2 reviewer-reply, R3 reviewer-reply,
R4 reviewer-reply).

Rounds are symmetric (4/4). All four issues reached `Converged` in Round 2
(§7c confirmations in `codex/round-2_reviewer-reply.md`). Rounds 3-4 contained
only procedural correction, convergence reconfirmation, and closure readiness
verification. No new arguments or convergence changes after Round 2.

---

## Key design decisions (for drafts/)

### Decision 1: Three pillars sufficient for v1 (X38-D-02)

**Accepted position**: Three architectural pillars — Contamination Firewall,
Protocol Engine, Meta-Updater — are sufficient for v1. No 4th pillar
(reproducibility engine, audit trail engine, ESP) required.

**Rejected alternative**: Keep pillar count structurally open pending Topic 017
(ESP). Possibly promote ESP or audit enforcement to a 4th pillar.

**Rationale**: Authority sources name exactly three mandatory components
(`docs/design_brief.md:34-90`; `PLAN.md:663-670`). Audit enforcement is
distributed across existing surfaces
(`debate/002-contamination-firewall/final-resolution.md:165-188`), not sourced
as a separate pillar. Topic 017 itself states ESP folds into Protocol Engine if
008 keeps three pillars
(`debate/017-epistemic-search-policy/findings-under-review.md:351-353`).
Responsibility mapping (making pillar assignments explicit to prevent Protocol
Engine from becoming a dumping ground) survives as documentation aid only — it
does not imply the pillar count is open.

Evidence: `claude_code/round-2_author-reply.md:42-84`,
`codex/round-2_reviewer-reply.md:39-57`.

### Decision 2: Directory structure confirmed (X38-D-09)

**Accepted position**: F-09's proposed directory tree
(`docs/design_brief.md:150-167`) stands unchanged. The surviving amendment is
strictly narrower: tighten the campaign-to-data checksum/manifest contract —
`campaign.json` MUST carry an explicit SHA-256 reference to its bound data
snapshot.

Open questions from F-09 resolved:
- `knowledge/` at root (mutable state, not source code)
- `data/` in project (reproducibility via co-location)
- `docs/` minimal (specs live in code, not separate documents)
- Separate venv (not shared with parent project)

**Rejected alternatives**:
(a) `specs/` root for versioned protocol specifications — conflates x38
design-authoring workflow (`x38_RULES.md:33-58`; `PLAN.md:676-692`) with
Alpha-Lab runtime (`docs/design_brief.md:150-167`). Protocol IS the code in
`src/alpha_lab/discovery/`.
(b) `state/`/`runtime/` root for governance state — no invariant violation
demonstrated. `PENDING_CLEAN_OOS` lives in `campaign.json`; cross-campaign
overview in `knowledge/campaigns_summary.json`. F-09's open questions
(`findings-under-review.md:114-117`) never mentioned `state/`.

**Rationale**: Snapshot identity via SHA-256 is the data-binding invariant
(`docs/design_brief.md:96-103,179-182`; `PLAN.md:445-447,581-599`). Whether
the system uses shared snapshots with manifest or per-campaign copies is an
operational policy decision, not architectural.

Evidence: `claude_code/round-2_author-reply.md:90-142`,
`codex/round-2_reviewer-reply.md:59-80`.

### Decision 3: Identity model — protocol_version axis (X38-D-13)

**Accepted position**: Add explicit `protocol_version` field to `campaign.json`
at creation time. Campaign lineage serves as `program_lineage_id` carrier via
existing `inherits_from` field. Cross-campaign convergence analysis MUST flag
comparisons across different protocol versions. Full change-trigger taxonomy
(what constitutes a version increment) deferred to Topics 003 (protocol
content) and 015 (semantic change classification).

**Rejected alternative**: Define major/minor/no-increment change-trigger
taxonomy now within Topic 008.

**Rationale**:
1. Cross-topic jurisdiction: Topic 003 owns protocol content, Topic 015 owns
   semantic change classification
   (`debate/001-campaign-model/final-resolution.md:164-170`;
   `debate/015-artifact-versioning/findings-under-review.md:92-99`). Defining
   bump semantics before 003 defines what protocol content IS pre-empts 003.
2. Gen4 import block: `docs/online_vs_offline.md:58-80` blocks importing gen4
   governance mechanics as offline template. The withdrawn taxonomy imported
   gen4's `constitution_version` increment semantics without adaptation.
3. Invariant enforceable without taxonomy: Topic 001's routing contract defaults
   to HANDOFF when protocol-identity preservation is unproven
   (`debate/001-campaign-model/final-resolution.md:121-143`). Conservative
   default works without 008 defining version increments.
4. Topic 010 consumer need answered: campaign lineage is a frozen required
   property (`debate/001-campaign-model/final-resolution.md:44-46`), carried via
   `inherits_from` (`findings-under-review.md:85-90`). Scenario 1 same-family
   comparison (`debate/010-clean-oos-certification/final-resolution.md:120-123,
   152-156`) answered by candidate-level contract (SSE-04-IDV), not another macro
   axis.

Evidence: `claude_code/round-2_author-reply.md:148-196`,
`codex/round-2_reviewer-reply.md:82-113`.

### Decision 4: Candidate-level identity vocabulary (X38-SSE-04-IDV)

**Accepted position**: A candidate-level identity contract is a required
architectural obligation, sitting ALONGSIDE D-13's macro provenance schema (not
inside it as a 4th macro axis).

Ownership split:
- **Topic 008**: existence obligation + structural pre-bucket fields (descriptor
  hash, parameter family, AST-hash subset)
- **Topic 013**: equivalence semantics (behavioral thresholds, hash granularity)
- **Topic 017**: consumption patterns (phenotype reconstruction-risk gate,
  cell-elite deduplication)

**Rejected alternative**: Promote candidate identity to a 4th macro axis inside
D-13's three-identity-axis model, creating a unified 4-axis identity schema
(protocol → campaign → session → candidate).

**Rationale**:
1. Abstraction-level mismatch: macro axes answer "in what context was this
   evidence produced?" (provenance metadata in `campaign.json`). Candidate
   identity answers "what structural entity is this?" (scan artifact metadata).
   Merging forces convergence analysis to carry provenance it doesn't need and
   forces Meta-Updater to process candidate hashes it doesn't consume.
2. Consumer topics claimed jurisdiction: Topic 013 owns structural-hash
   granularity and behavioral equivalence thresholds
   (`debate/013-convergence-analysis/findings-under-review.md:215-219`). Topic
   017 owns phenotype and structural-prior consumption
   (`debate/017-epistemic-search-policy/findings-under-review.md:102-123,
   143-165`).
3. Topic 018 already separated `identity_vocabulary` from `equivalence_method`
   (`debate/018-search-space-expansion/final-resolution.md:122-155,306-319`).
4. Serves Topic 010's deferred Scenario 1 same-family comparison need
   (`debate/010-clean-oos-certification/final-resolution.md:120-123,152-156,
   176-177`) without overloading D-13.

Evidence: `claude_code/round-2_author-reply.md:200-257`,
`codex/round-2_reviewer-reply.md:115-139`.

---

## Unresolved tradeoffs (for human review)

- **Protocol version bump taxonomy**: Deferred to Topics 003 (protocol content)
  and 015 (semantic change classification). When both close, the full taxonomy
  (what constitutes a version increment) should be reconciled with D-13's
  `protocol_version` field. Risk: if 003 and 015 close without coordinating on
  bump semantics, the field remains underspecified.

- **Candidate-level structural-hash granularity**: Topic 008 declares existence
  obligation and structural pre-bucket fields. Topic 013 owns semantic details
  (equivalence thresholds, hash granularity). If 013 closes without specifying
  these, the identity contract remains structurally defined but semantically
  incomplete.

- **SSE-04-IDV status**: Routed from Topic 018. Topic 018 re-closed (2026-03-27)
  under standard 2-agent debate — 7-field breadth-activation contract confirmed
  unchanged (SSE-D-04). Field 3 ownership (`identity_vocabulary`) resolved
  authoritatively via Topic 008 Decision 4 (SSE-04-IDV). No longer provisional.

---

## Agreed elements (stable since Round 2, both agents)

These were never disputed and are carried forward as frozen law:

1. Three pillars: Contamination Firewall, Protocol Engine, Meta-Updater
2. Directory tree: `src/alpha_lab/`, `data/`, `campaigns/`, `knowledge/`,
   `tests/` (as in `design_brief.md:150-167`)
3. Campaign-to-data binding: SHA-256 checksum as identity invariant
4. `protocol_version` field in `campaign.json` (mandatory at creation)
5. `inherits_from` in `campaign.json` carries campaign lineage
6. Candidate-level identity contract: alongside (not inside) D-13

---

## Cross-topic impact

| Topic | Impact | Action needed |
|-------|--------|---------------|
| 017 (epistemic search policy) | 008 closure satisfies one dependency (002✅ + **008✅** + 010✅ + 013). ESP pillar decision frozen: 3 pillars, ESP folds into Protocol Engine. | Update EXECUTION_PLAN.md dependency. 017 starts once 013 also closes. |
| 015 (artifact versioning) | 008 closure satisfies soft-dep (007✅ + **008✅**). `protocol_version` axis provides identity reference for F-17 semantic change classification. | 015 consumes `protocol_version` schema when defining change-trigger taxonomy. |
| 013 (convergence analysis) | SSE-04-IDV provides structural pre-bucket for convergence equivalence metrics. | 013 consumes SSE-04-IDV interface when defining behavioral equivalence thresholds. |
| 010 (clean OOS, CLOSED) | Scenario 1 (same-family rediscovery) deferred to 008 — now answered: campaign lineage via `inherits_from` + candidate-level contract via SSE-04-IDV. | No action — 010 closed, consumes these interfaces. |
| 009 (data integrity) | Directory structure confirmed: `data/` in project, checksum-bound campaigns. | 009 may reference F-09's confirmed tree for F-10/F-11. |
| 005 (core engine) | Pillar boundaries frozen: 3 pillars. Engine within Firewall + Protocol Engine. | 005 designs within confirmed pillar boundaries. |
| 006 (feature engine) | Feature engine is Protocol Engine sub-component (Stages 3-4). | 006 designs within Protocol Engine pillar. |
| 003 (protocol engine, Wave 3) | `protocol_version` feeds protocol stage design. ESP → Protocol Engine sub-component (not 4th pillar). | 003 consumes D-13 identity schema + D-02 pillar assignment. |

---

## Draft impact

| Draft | Sections affected | Action needed |
|-------|------------------|---------------|
| `architecture_spec.md` | §2 (Identity Model & Provenance) | **Create**: `protocol_version` + `inherits_from` in `campaign.json`, cross-protocol flagging |
| `architecture_spec.md` | §3 (Directory Structure) | **Create**: confirmed tree from F-09, checksum contract, venv policy |
| `architecture_spec.md` | §6.5 (Pre-existing Candidates) | **Verify**: Scenario 1 consumption path answered by D-13 + SSE-04-IDV |
| `architecture_spec.md` | Traceability table | **Add**: D-02, D-09, D-13, SSE-04-IDV entries |
| `meta_spec.md` | §8 (Protocol Version Impact on Meta-Knowledge) | **Create**: `protocol_version` impact on meta-knowledge governance |
