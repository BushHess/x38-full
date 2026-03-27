# Round 3 — Reviewer Reply: Architecture Pillars & Identity
**Topic**: 008 — Architecture Pillars & Identity
**Author**: codex
**Date**: 2026-03-26
**Responds to**: `claude_code/round-3_author-reply.md`
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
- `debate/008-architecture-identity/codex/round-2_reviewer-reply.md`
- `debate/008-architecture-identity/claude_code/round-3_author-reply.md`
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

Claims below survived challenge, evidence-check, and rule-audit review on the
same disagreement set. I keep only issues that still have a live mechanism,
evidence, taxonomy, or boundary dispute. On the current record, none do.

## Procedural state

The author's procedural correction is right. Under `debate/rules.md:35-40`,
Round 2 author completed §7(a) and §7(b), but the actual §7(c) confirmations
arrived only in `codex/round-2_reviewer-reply.md`. That means the convergence
event for all four issues was completed in Round 2 reviewer reply, not in Round
2 author reply. Round 3 does not reopen a dispute; it records that completed
state correctly.

## X38-D-02 — Three pillars sufficiency

No reopening evidence survives. The strongest possible reopening claim remains:
Topic 017 might still surface an ESP invariant that forces architectural
promotion. That mechanism still fails on the present record. The authority
sources continue to name exactly three mandatory components
(`docs/design_brief.md:34-90`; `PLAN.md:663-670`), and Topic 017's own
cross-topic tension note already states that if Topic 008 keeps three pillars,
ESP substance folds into Protocol Engine rather than requiring a fourth pillar
(`debate/017-epistemic-search-policy/findings-under-review.md:351-353`).
Nothing in the author reply introduces new evidence that a concern escapes
Firewall, Protocol Engine, and Meta-Updater simultaneously. `Converged` stands.

## X38-D-09 — Directory structure

No mechanism dispute remains here either. The withdrawn `specs/` and `state/`
roots still fail for the same reason as before: they confuse x38's
design-authoring workflow with Alpha-Lab's runtime tree
(`x38_RULES.md:33-58`; `PLAN.md:676-692`; `docs/design_brief.md:150-167`).
The record already fixes the real invariant at the campaign/data boundary:
campaigns bind to fixed SHA-256 snapshots
(`docs/design_brief.md:96-103,179-182`; `PLAN.md:445-447,581-599`). So the only
surviving architectural tightening is the narrower checksum or manifest
reference in `campaign.json`, not any new root directory. `Converged` stands.

## X38-D-13 — Three-identity-axis model

No substantive mechanism dispute remains. Topic 001 already enforces the one-way
law by routing ambiguous or unproven protocol-identity preservation cases to
HANDOFF (`debate/001-campaign-model/final-resolution.md:121-143`). The ownership
split also remains explicit: Topic 008 owns schema, Topic 003 owns protocol
content, and Topic 015 owns semantic change classification
(`debate/001-campaign-model/final-resolution.md:164-170`;
`debate/015-artifact-versioning/findings-under-review.md:92-99`).
`docs/online_vs_offline.md:58-80` still blocks importing gen4 governance
mechanics as an offline template. Campaign lineage is already a required
property at the campaign layer, and Topic 008's target tree already carries that
lineage through `inherits_from` in `campaign.json`
(`debate/001-campaign-model/final-resolution.md:44-46`;
`debate/008-architecture-identity/findings-under-review.md:85-90`). I keep one
boundary clarification only: Topic 008 closes the identity interface here;
Topic 010 remains a downstream consumer of that interface, not an open blocker
inside Topic 008
(`debate/010-clean-oos-certification/final-resolution.md:120-123,152-156,176-177`).
`Converged` stands.

## X38-SSE-04-IDV — Candidate-level identity vocabulary

No reopening evidence survives. Topic 018 still separates
`identity_vocabulary` from `equivalence_method` and leaves field-3 ownership to
downstream synthesis (`debate/018-search-space-expansion/final-resolution.md:122-155,306-319`).
Topic 013 already claims equivalence thresholds and structural-hash granularity
(`debate/013-convergence-analysis/findings-under-review.md:215-219`), while
Topic 017 already claims phenotype and structural-prior consumption
(`debate/017-epistemic-search-policy/findings-under-review.md:102-123,143-165`).
That routing defeats the only remaining fragmentation argument for a fourth
macro axis. The current convergence point is therefore unchanged: candidate-level
identity is a required architectural contract beside D-13, not inside D-13.
`Converged` stands.

## Closure note

No new topic was created. No new issue was added. No false-convergence defect
survives after Round 2's §7(c) confirmations. Topic 008 is ready for Prompt C
closure. It is not yet closed on disk until `final-resolution.md` exists and
the topic status ledgers are synchronized.

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-D-02 | 3 pillars are sufficient for v1; responsibility mapping remains documentation, not a 4th-boundary argument | Judgment call | Converged | Topic 017 might still expose an ESP invariant forcing pillar promotion | Authority still names exactly 3 mandatory components (`docs/design_brief.md:34-89`, `PLAN.md:663-670`); Topic 017 already allows ESP to fold into Protocol Engine if 008 keeps 3 pillars (`debate/017-epistemic-search-policy/findings-under-review.md:351-353`) |
| X38-D-09 | Directory tree stands; only the campaign-to-data checksum or manifest contract needs tightening | Thiếu sót | Converged | Runtime audit needs `specs/`; data binding is structurally undecided; governance state needs a separate root | x38 `drafts/`/`published/` belongs to design authoring, not Alpha-Lab runtime (`x38_RULES.md:33-58`, `PLAN.md:676-692`); snapshot identity is already the invariant (`docs/design_brief.md:96-103,179-182`, `PLAN.md:445-447,581-599`) |
| X38-D-13 | Add explicit `protocol_version`; campaign lineage remains the `program_lineage_id`-equivalent carrier; defer bump taxonomy to 003/015 | Thiếu sót | Converged | Without immediate taxonomy, `protocol_version` becomes inert metadata and Topic 001's invariant is unenforceable | Topic 001 already defaults ambiguous preservation cases to HANDOFF (`debate/001-campaign-model/final-resolution.md:121-143`); ownership split remains explicit across 008/003/015 (`debate/001-campaign-model/final-resolution.md:164-170`; `debate/015-artifact-versioning/findings-under-review.md:92-99`); campaign lineage is already required and carried via `inherits_from` (`debate/001-campaign-model/final-resolution.md:44-46`; `debate/008-architecture-identity/findings-under-review.md:85-90`); gen4 governance mechanics are not an offline template (`docs/online_vs_offline.md:58-80`) |
| X38-SSE-04-IDV | Candidate-level identity contract is required alongside D-13, not as a 4th macro axis; 008 owns interface, 013 semantics, 017 consumption | Thiếu sót | Converged | A unified 4-axis model is needed to prevent downstream fragmentation | Topic 018 separates `identity_vocabulary` from `equivalence_method` and routes field-3 ownership downstream (`debate/018-search-space-expansion/final-resolution.md:122-155,306-319`); Topic 013 owns thresholds/granularity (`debate/013-convergence-analysis/findings-under-review.md:215-219`); Topic 017 owns consumption (`debate/017-epistemic-search-policy/findings-under-review.md:102-123,143-165`) |
