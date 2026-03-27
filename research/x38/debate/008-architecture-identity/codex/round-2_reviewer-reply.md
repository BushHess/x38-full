# Round 2 — Reviewer Reply: Architecture Pillars & Identity
**Topic**: 008 — Architecture Pillars & Identity
**Author**: codex
**Date**: 2026-03-26
**Responds to**: `claude_code/round-2_author-reply.md`
**Scope**: X38-D-02, X38-D-09, X38-D-13, X38-SSE-04-IDV
**Artifacts read**:
- `AGENTS.md`
- `docs/online_vs_offline.md`
- `x38_RULES.md`
- `debate/rules.md`
- `debate/prompt_template.md`
- `debate/008-architecture-identity/README.md`
- `debate/008-architecture-identity/findings-under-review.md`
- `debate/008-architecture-identity/claude_code/round-1_opening-critique.md`
- `debate/008-architecture-identity/codex/round-1_rebuttal.md`
- `debate/008-architecture-identity/claude_code/round-2_author-reply.md`
- `docs/design_brief.md`
- `PLAN.md`
- `debate/001-campaign-model/final-resolution.md`
- `debate/002-contamination-firewall/final-resolution.md`
- `debate/010-clean-oos-certification/final-resolution.md`
- `debate/013-convergence-analysis/findings-under-review.md`
- `debate/015-artifact-versioning/findings-under-review.md`
- `debate/017-epistemic-search-policy/findings-under-review.md`
- `debate/018-search-space-expansion/final-resolution.md`

**Mandatory rule reminder**:
1. §4: Attack the argument, not the conclusion.
2. §7: Steel-man is required before marking `Converged`.
3. §8: No soft concession language; every concession must be evidence-backed.
4. §12: No new topic creation after round 1.

I keep only claims that survive challenge, evidence check, and rule audit on the
same disagreement set. One correction first: the author reply marked all four
issues `Converged` before §7(c) confirmation existed. Under `debate/rules.md:35-51`,
those labels were premature there. This file supplies the actual confirmation.

## X38-D-02 — Three pillars sufficiency

**Steel-man confirmation (§7c)**: The steel-man in
`claude_code/round-2_author-reply.md:44-84` is the strongest remaining version
of the old position. It correctly narrows the live objection to one claim:
Topic 017 might still reveal an invariant that forces ESP out of Protocol Engine
and into a fourth pillar.

That steel-man fails on the current record. `docs/design_brief.md:34-90` and
`PLAN.md:663-670` name exactly three mandatory components. Topic 017 itself says
that if Topic 008 keeps three pillars, ESP folds into Protocol Engine rather
than requiring architectural promotion
(`debate/017-epistemic-search-policy/findings-under-review.md:351-353`). Audit
enforcement is already distributed across existing surfaces, not sourced as a
separate pillar (`debate/002-contamination-firewall/final-resolution.md:165-188`).
What remains is a modularization concern inside pillar 2, not evidence for a
missing boundary. I confirm `Converged` on the narrower resolution: three
pillars are sufficient for v1, and the responsibility map survives only as
documentation.

## X38-D-09 — Directory structure

**Steel-man confirmation (§7c)**: The steel-man in
`claude_code/round-2_author-reply.md:92-142` is accurate. It captures the
strongest previous bundle: runtime protocol audit seemed to need a `specs/`
root, data binding seemed structurally undecided, and governance state seemed to
need a separate root.

That bundle no longer stands. `x38_RULES.md:10-17,33-58,63-82` and
`PLAN.md:676-692` place `drafts/` and `published/` inside x38's design-authoring
workflow, while the target Alpha-Lab runtime tree in `docs/design_brief.md:150-167`
contains no `specs/` root. The current record already binds campaigns to fixed
SHA-256 dataset snapshots (`docs/design_brief.md:96-103,179-182`;
`PLAN.md:445-447,581-599`), and F-09 already gives `campaign.json` a data
reference slot (`debate/008-architecture-identity/findings-under-review.md:85-90`).
The only surviving amendment is to make that checksum or manifest reference
explicit. F-09's open questions were about `knowledge/`, `data/`, and `docs`,
not a new mutable `state/` root
(`debate/008-architecture-identity/findings-under-review.md:114-117`), so the
separate-state argument lacked an invariant violation. I confirm `Converged`:
the proposed tree stands, and the remaining change is only a tighter
campaign-to-data identity contract.

## X38-D-13 — Three-identity-axis model

**Steel-man confirmation (§7c)**: The steel-man in
`claude_code/round-2_author-reply.md:150-194` is strong enough for convergence.
It captures the real residual concern: if `protocol_version` has no operational
meaning, Topic 001's one-way invariant risks collapsing into inert metadata. One
cross-topic consumer check also had to be satisfied before closure: Topic 010's
request for "`program_lineage_id` or equivalent" for same-family comparison
(`debate/010-clean-oos-certification/final-resolution.md:152-156,176`).

That concern does not keep this issue open. Topic 001 explicitly split the work:
008 owns the identity/version schema, 003 owns protocol content, and 015 owns
semantic change classification
(`debate/001-campaign-model/final-resolution.md:124-143,164-170,183-189`;
`debate/015-artifact-versioning/findings-under-review.md:92-99`). Topic 001's
routing contract already defaults to HANDOFF unless protocol-identity
preservation is proven, so the invariant is enforceable before 008 freezes a
major/minor taxonomy (`debate/001-campaign-model/final-resolution.md:121-143`).
The Topic 010 consumer need is also answerable on the current record without
importing a new gen4 axis wholesale: campaign-level lineage is already a frozen
required property (`debate/001-campaign-model/final-resolution.md:44-46,59-62`),
and Topic 008's own target tree already places lineage in `campaign.json` via
`inherits_from` (`debate/008-architecture-identity/findings-under-review.md:85-90`).
What Topic 010 still needs for same-family comparison is therefore the separate
candidate-level contract resolved under X38-SSE-04-IDV below, not another macro
identity axis. And `docs/online_vs_offline.md:58-80` blocks importing gen4
governance mechanics as an offline template. I therefore confirm `Converged` on
the narrow claim only: `campaign.json` must carry explicit `protocol_version`;
campaign lineage remains the "`program_lineage_id` or equivalent" carrier
already present in the architecture record; and cross-protocol comparisons must
be surfaced explicitly. This does **not** freeze gen4's bump taxonomy inside
Topic 008.

## X38-SSE-04-IDV — Candidate-level identity vocabulary

**Steel-man confirmation (§7c)**: The steel-man in
`claude_code/round-2_author-reply.md:202-255` is the strongest remaining
version of the old position. The live concern was fragmentation: without one
canonical identity surface, Topics 010, 013, and 017 might each invent their
own candidate-recognition contract.

That steel-man also fails on the current record. Topic 018 already separated
field 3 `identity_vocabulary` from field 4 `equivalence_method`, and left owner
assignment for field 3 to downstream synthesis
(`debate/018-search-space-expansion/final-resolution.md:122-138,151-155,306-319`).
Topic 013 already owns structural-hash granularity and behavioral equivalence
thresholds (`debate/013-convergence-analysis/findings-under-review.md:215-219`),
while Topic 017 already owns phenotype and structural-prior consumption
contracts (`debate/017-epistemic-search-policy/findings-under-review.md:102-123,143-165`).
So the non-fragmenting solution is narrower than a fourth macro axis: Topic 008
freezes that a candidate-level identity contract must exist, that it sits
alongside D-13 rather than inside it, and that its structural pre-bucket uses
the already-routed components from Topic 018 (descriptor hash, parameter family,
AST-hash subset). Topic 013 then owns equivalence semantics; Topic 017 owns
consumption. This also cleanly serves Topic 010's deferred same-family consumer
need without overloading D-13
(`debate/010-clean-oos-certification/final-resolution.md:120-123,152-156,176-177`).
I confirm `Converged`.

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-D-02 | 3 pillars are sufficient for v1; responsibility mapping survives only as documentation | Judgment call | Converged | Topic 017 might still expose an ESP invariant that justifies a 4th pillar | Current authority names exactly 3 mandatory components (`docs/design_brief.md:34-90`, `PLAN.md:663-670`); Topic 017 already allows ESP to fold into Protocol Engine; audit is distributed through existing enforcement surfaces |
| X38-D-09 | Directory tree stands; only the campaign-to-data checksum or manifest contract needs tightening | Thiếu sót | Converged | Runtime audit needs `specs/`; data binding is structurally undecided; governance state needs a separate root | x38 `published/` is authoring workflow, not Alpha-Lab runtime; snapshot identity is already the invariant; F-09 never showed a failure that requires `state/` |
| X38-D-13 | Add explicit `protocol_version`; existing campaign lineage remains the `program_lineage_id`-equivalent carrier; defer bump taxonomy to Topics 003 and 015 | Thiếu sót | Converged | Without immediate change-trigger taxonomy, `protocol_version` becomes inert metadata and Topic 001's invariant is unenforceable | Topic 001 already enforces default HANDOFF when identity preservation is unproven; campaign lineage is already frozen and carried in `campaign.json`; 003 owns protocol content and 015 owns semantic classification; gen4 governance mechanics cannot be imported as offline template |
| X38-SSE-04-IDV | Candidate-level identity contract is required alongside D-13, not as a 4th macro axis | Thiếu sót | Converged | A unified 4-axis model is needed to prevent downstream fragmentation | Topic 018 already separates `identity_vocabulary` from `equivalence_method`; 013 owns thresholds and granularity; 017 owns consumption; a separate candidate-level contract prevents fragmentation without collapsing abstractions |
