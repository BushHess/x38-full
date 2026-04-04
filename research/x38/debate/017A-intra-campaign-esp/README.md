# Topic 017A — Intra-Campaign ESP (v1 Scope)

**Topic ID**: X38-T-17A
**Opened**: 2026-04-03
**Status**: OPEN (backlog — activate after Wave 2 prerequisites close)
**Origin**: Split from Topic 017 (2026-04-03). Topic 017 had 6 findings (488 lines,
212-line README, 10 cross-topic tensions) — too complex for a single debate unit.
Split into 2 sub-topics along the v1/v2 scope boundary already identified in
017's internal staging (Stage A/B).

017A contains the **v1-implementable** ESP decisions: what a single campaign
PRODUCES (coverage, cell-elite archive, epistemic_delta) and how it ALLOCATES
compute (budget governor). These must close before Topic 003 (protocol engine)
can finalize v1 pipeline stages.

## Problem statement

x38's 3 pillars are defensive but lack a mechanism to improve search efficiency
within a campaign. Stage 4 (F-05) collapses diversity via global top-K pruning.
No coverage tracking exists. Campaign endings produce verdict.json but no
structured epistemic output documenting what was LEARNED about the search space.

Topic 017A addresses this with 3 findings:

1. **ESP-01** (Intra-campaign illumination): Modifies Stages 3-8 to add descriptor
   tagging, cell-elite archive (replaces global top-K), coverage map, and mandatory
   epistemic_delta.json output.
2. **ESP-04** (Budget governor): 3-compartment budget (coverage_floor, exploit,
   contradiction_resurrection) with anti-ratchet mechanism.
3. **SSE-04-CELL** (Cell-axis values): 4 mandatory cell axes from Topic 018,
   numeric thresholds for anomaly detection, proof bundle consumption rules.

## Scope

3 findings, structural + parametric decisions:

| ID | Finding | Key decisions |
|----|---------|---------------|
| ESP-01 | Intra-campaign illumination (Stages 3-8) | Cell-elite vs global top-K? epistemic_delta mandatory/advisory? Coverage map format? |
| ESP-04 | Budget governor & anti-ratchet | Coverage floor per cell? Exploit budget cap? Periodic audit frequency? |
| SSE-04-CELL | Cell-axis values + anomaly thresholds | Categories per axis? Threshold type (absolute/relative)? Proof bundle pass criteria? |

**Plus**: 013↔017 circular dependency resolution (interface contracts between
convergence metrics and ESP consumption).

This topic does NOT own:
- CandidatePhenotype / StructuralPrior contracts (017B)
- Inter-campaign promotion ladder (017B)
- Contradiction consumption semantics (017B)
- Pipeline stage structure (003)
- Artifact enumeration (015)
- Feature family taxonomy (006)
- Bounded recalibration (016)

## Evidence base

**Convergence notes** (shared reference at `../000-framework-proposal/`):
- **C-01**: MK-17 != primary evidence; firewall = main pillar
- **C-02**: Shadow-only principle settled
- **C-12**: Answer priors banned ALWAYS

**Closed topic invariants** (non-negotiable):
- Topic 004 MK-17: Same-dataset empirical priors = shadow-only
- Topic 004 C3 (converged): "Budget split = v2+ design. V1: all search is frontier."
  ESP-04 must reconcile with this constraint.
- Topic 007 F-01: "Inherit methodology, not answers"
- Topic 007 F-22: Phase 1 evidence taxonomy (3 types frozen)
- Topic 007 F-25: Regime-aware policy: internal conditional logic ALLOWED,
  external classifiers FORBIDDEN
- Topic 001 D-16: protocol_identity_change → new_campaign (one-way invariant)
- Topic 018 SSE-D-04: 4 mandatory cell axes (mechanism_family, architecture_depth,
  turnover_bucket, timeframe_binding), confirmed 2026-03-27

**Empirical evidence** [extra-archive]:
- V4→V8: 5 sessions, 5 different winners, same "D1 slow" family — no coverage
  tracking between sessions
- Gen3 V1: FAILED (NO_ROBUST_CANDIDATE), 4 structural gaps — no epistemic output
- X12-X19 churn research: 8 studies, structural insights not systematically captured

## Dependencies

- **Hard upstream** (all CLOSED):
  - Topic 002 (contamination firewall, CLOSED 2026-03-25)
  - Topic 008 (architecture & identity, CLOSED 2026-03-27) — 3 pillars sufficient
    for v1; ESP folds into Protocol Engine as sub-component
  - Topic 010 (Clean OOS, CLOSED 2026-03-25) — D-24 method-first power contract
  - Topic 013 (convergence analysis, CLOSED 2026-03-28) — coverage metrics,
    deferred numerics require 017A outputs
  - Topic 018 (search-space expansion, CLOSED 2026-03-27) — SSE-04-CELL routed
- **HARD UPSTREAM DEPS SATISFIED** — all pre-requisite topics closed.
  **NOTE**: Topic 013 deferred 3 items (robustness bundle minimum, consumption
  sufficiency, anomaly numerics) pending 017A's consumption contract. These do
  NOT block 017A debate — but 013's final numerics will be resolved AFTER 017A
  closes, as a post-closure integration step (Topic 003). See 013↔017 resolution
  in findings-under-review.md.
- **Hard downstream**:
  - Topic 017B (inter-campaign ESP) — needs cell-axis categories + descriptor taxonomy
  - Topic 003 (protocol engine) — needs v1 stage modifications

## Wave assignment

**Wave 2.5**: Song song với Topic 016 (bounded recalibration) và Topic 019.
017A KHÔNG depend 017B — 017B depends on 017A.

**Scheduling benefit of split**: 003 can begin once 017A closes, without waiting
for 017B (v2 contracts). 017B can debate in parallel with 003 if needed — v2
features don't affect v1 pipeline structure.

## Debate plan

- Estimated: 2 rounds
- **Two-pass within topic** (structural then parametric):

  **Pass 1 — Structural**:
  - SSE-04-CELL: 4 axis categories (what dimensions define a cell?)
  - ESP-01: descriptor taxonomy, cell-elite archive design, epistemic_delta schema
  - 013↔017 interface contracts

  **Pass 2 — Parametric**:
  - ESP-04: coverage floor per cell, exploit budget cap %, periodic audit N
  - SSE-04-CELL: anomaly thresholds, proof bundle pass criteria
  - ESP-01: mandatory vs advisory status for each output

- **Pre-debate anchor option**: Human researcher proposes candidate SSE-04-CELL axis
  categories and anomaly thresholds based on Topic 018 evidence and x37 research.
  These are INPUT to the debate, not pre-resolved — debaters may accept, modify,
  or reject them.
- **Pressure-test requirement**: Verify that v1 budget compartments (coverage_floor +
  exploit) are logically sufficient WITHOUT v2 contradiction_resurrection. Do not
  defer sufficiency validation to 017B.

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 003 | F-05 | Cell-elite archive changes Stage 4 design. epistemic_delta.json adds Stage 8 mandatory output. Descriptor tagging adds Stage 3 output. | 003 owns pipeline structure; 017A defines ESP component contracts. |
| 006 | F-08 | Phenotype descriptor taxonomy overlaps feature family taxonomy. | 006 owns feature-level; 017A owns strategy-level. Must not conflict. |
| 013 | CA-01 | Coverage metrics overlap. Budget governor interacts with stop conditions. 013↔017 circular dependency on deferred numerics. | 013 owns convergence/stop; 017A defines coverage obligations + breaks dependency cycle via interface contracts. |
| 004 | C3 | "Budget split = v2+ design. V1: all search is frontier." ESP-04 budget compartments may constitute budget split. | 017A must reconcile: ordering within frontier ≠ budget split. Requires debate. |
| 016 | BR-01 | ESP MUST NOT suggest parameter directions — answer-level influence. | Explicit scope exclusion. |
| 017B | ESP-02 | 017B needs cell-axis categories from SSE-04-CELL (017A) for phenotype descriptors. | 017A closes first → 017B consumes. |
| 017B | SSE-08-CON | Contradiction resurrection (017B) may override ESP-04 budget governor anti-ratchet (017A). | 017A owns budget rules; 017B defines consumption that respects them. |

## Files

| File | Purpose |
|------|---------|
| `findings-under-review.md` | 3 findings: ESP-01, ESP-04, SSE-04-CELL + 013↔017 resolution strategy |
| `claude_code/` | Critique from Claude Code |
| `codex/` | Critique from Codex |
