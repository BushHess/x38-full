# Topic 017B — Inter-Campaign ESP (v2 Scope)

**Topic ID**: X38-T-17B
**Opened**: 2026-04-03
**Status**: OPEN (backlog — activate after 017A closes)
**Origin**: Split from Topic 017 (2026-04-03). Topic 017 had 6 findings (488 lines,
212-line README, 10 cross-topic tensions) — too complex for a single debate unit.
Split into 2 sub-topics along the v1/v2 scope boundary.

017B contains the **v2-scope** ESP decisions: inter-campaign phenotype memory
contracts, promotion ladder, and contradiction consumption semantics. These are
storage infrastructure decisions — v1 BUILDS the storage (OBSERVED,
REPLICATED_SHADOW entries) but DEFERS activation logic. The primary question is
whether to implement storage now (evidence accumulation) or defer entirely (YAGNI).

## Problem statement

After a campaign ends, ALL epistemic output is locked in that campaign's
artifacts. No mechanism carries phenotype-level knowledge (NOT answers) to
the next campaign. Each campaign starts from zero understanding of the search
space structure, despite prior campaigns having explored overlapping regions.

Topic 017B addresses this with 3 findings:

1. **ESP-02** (CandidatePhenotype & StructuralPrior contracts): Typed schema
   for sanitized phenotype descriptors with reconstruction-risk gate. Forbidden
   payload (feature names, parameters, winner IDs) enforced at schema level.
2. **ESP-03** (Inter-campaign promotion ladder): 4-rung lifecycle
   (OBSERVED → REPLICATED_SHADOW → ACTIVE → DEFAULT_METHOD_RULE).
   v1 reality: all priors stuck at OBSERVED/REPLICATED_SHADOW (context distance=0).
3. **SSE-08-CON** (Contradiction consumption semantics): How surprise queue
   references contradiction entries, resurrection triggers, proof bundle
   integration.

## Scope

3 findings, primarily v2-scope decisions:

| ID | Finding | Key decisions |
|----|---------|---------------|
| ESP-02 | CandidatePhenotype & StructuralPrior contracts | Reconstruction-risk threshold? Descriptor dimensions: fixed/extensible? |
| ESP-03 | Inter-campaign promotion ladder | Build v1 storage (YAGNI risk) or defer (evidence loss risk)? Context distance definition? |
| SSE-08-CON | Contradiction consumption semantics | Resurrection threshold? Shadow vs active interaction? Budget governor override? |

This topic does NOT own:
- Intra-campaign illumination, cell axes, budget governor (017A)
- Pipeline stage structure (003)
- Artifact enumeration + invalidation rules (015)
- Feature family taxonomy (006)
- Firewall content rules (002, CLOSED)

## Evidence base

**Convergence notes** (shared reference at `../000-framework-proposal/`):
- **C-01**: MK-17 != primary evidence; firewall = main pillar
- **C-02**: Shadow-only principle settled
- **C-12**: Answer priors banned ALWAYS

**Closed topic invariants** (non-negotiable):
- Topic 004 MK-17: Same-dataset empirical priors = shadow-only
- Topic 002 F-04 (CLOSED 2026-03-25): NO vocabulary expansion, NO STRUCTURAL_PRIOR
  category. Permanent path: UNMAPPED + Tier 2 + SHADOW.
- Topic 007 F-01: "Inherit methodology, not answers"
- Topic 010 D-24 (CLOSED 2026-03-25): Method-first power contract frozen.
  ESP-03 consumes D-24 for promotion decisions.

**Empirical evidence** [extra-archive]:
- research/x37/docs/gen1/RESEARCH_PROMPT_V6/CONTAMINATION_LOG_V2.md: every online
  session leaked answer priors through "methodology" lessons — phenotype contract
  with forbidden_payload prevents this at schema level

## Dependencies

- **Hard upstream** (all CLOSED):
  - Topic 002, 008, 010, 013, 018 — same as 017A, all CLOSED
- **Hard upstream** (OPEN):
  - **Topic 017A** — needs cell-axis categories (SSE-04-CELL) + descriptor taxonomy
    (ESP-01) to define phenotype dimensions and reconstruction-risk computation
- **Soft downstream**:
  - Topic 015 (artifact/versioning) — ESP-02 introduces 3+ new artifacts
    (phenotype_pack, prior_registry, comparison_set). 015 must enumerate.
  - Topic 003 (protocol engine) — v2 contracts inform Stage 7/8 output slots
    but don't change v1 pipeline structure

## Wave assignment

**Wave 2.5**: Sequential after 017A. Can debate in parallel with Topic 003
(Wave 3) if 017A has closed — v2 features don't affect v1 pipeline stages.

**Key implication**: 003 does NOT need 017B to close before starting. 003 only
needs 017A. This was the primary scheduling benefit of the 017 split.

## Debate plan

- Estimated: 1-2 rounds
- Key battles:
  - ESP-02: Reconstruction-risk gate threshold (too strict = phenotype useless,
    too loose = firewall bypass). BTC/USDT single-asset: most descriptors have
    high reconstruction risk → what's the minimum useful coarsening?
  - ESP-03: Build v1 storage or defer? Strong arguments both ways (evidence
    accumulation vs YAGNI). v1 reality check: context distance=0 means all
    priors stuck at shadow. Is the storage worth building for zero v1 activation?
  - SSE-08-CON: Contradiction resurrection trigger design. Interaction with
    budget governor anti-ratchet (017A ESP-04).

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 002 | F-04 | Reconstruction-risk gate extends firewall enforcement to phenotype layer. **RESOLVED**: 002 CLOSED — NO vocabulary expansion. Phenotype operates within 3-category + UNMAPPED boundary. | 002 CLOSED; 017B designs within constraint. |
| 010 | F-24 | Power floors for promotion ladder reuse Clean OOS power methodology. **RESOLVED**: 010 CLOSED — D-24 method-first power contract frozen. | 010 CLOSED; 017B consumes D-24. |
| 015 | F-14, F-17 | ESP introduces new mandatory artifacts. F-14 must enumerate; F-17 must classify invalidation. | 015 owns enumeration; 017B defines contracts. |
| 017A | ESP-04 | SSE-08-CON contradiction resurrection may override budget governor anti-ratchet. | 017A owns budget rules; 017B defines consumption that must respect them. |

## Files

| File | Purpose |
|------|---------|
| `findings-under-review.md` | 3 findings: ESP-02, ESP-03, SSE-08-CON |
| `claude_code/` | Critique from Claude Code |
| `codex/` | Critique from Codex |
