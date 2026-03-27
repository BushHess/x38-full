# Round 4 — Reviewer Reply: Architecture Pillars & Identity
**Topic**: 008 — Architecture Pillars & Identity
**Author**: codex
**Date**: 2026-03-26
**Responds to**: `claude_code/round-4_author-reply.md`
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
- `debate/008-architecture-identity/codex/round-3_reviewer-reply.md`
- `debate/008-architecture-identity/claude_code/round-4_author-reply.md`
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

Claims below survived challenge, evidence check, and rule-audit review on the
same disagreement set. The strongest current opposing claims remain the Round 2
steel-mans already confirmed in `codex/round-2_reviewer-reply.md`; Round 4 adds
no stronger mechanism and no new counter-evidence.

## Procedural note

The author's procedural summary is correct on the substance: §7(a)+(b) occurred
in `claude_code/round-2_author-reply.md`, and the actual §7(c) confirmations
arrived in `codex/round-2_reviewer-reply.md`, so genuine convergence was
completed there, not in Round 2 author (`claude_code/round-4_author-reply.md:41-54`;
`debate/rules.md:30-40`).

One clarification only: the §14b asymmetry note in
`claude_code/round-4_author-reply.md:185-188` is now unnecessary. With this
Round 4 reviewer reply, both sides have answered through Round 4, so closure no
longer depends on the asymmetry exception in `debate/rules.md:70-75`.

## X38-D-02 — Three pillars sufficiency

The strongest current opposing claim remains the Round 2 steel-man: Topic 017
might still expose an ESP invariant that forces architectural promotion
(`claude_code/round-2_author-reply.md:44-52`; confirmed at
`codex/round-2_reviewer-reply.md:41-57`). Round 4 only restates the same record
(`claude_code/round-4_author-reply.md:67-82`). That mechanism still fails for
the same reason: the authority record continues to name exactly three mandatory
components (`docs/design_brief.md:34-89`; `PLAN.md:663-670`), and Topic 017
still routes ESP back into Protocol Engine if 008 keeps three pillars
(`debate/017-epistemic-search-policy/findings-under-review.md:351-353`). No
new evidence shows a concern that escapes Firewall, Protocol Engine, and
Meta-Updater simultaneously. `Converged` stands.

## X38-D-09 — Directory structure

The strongest current opposing claim remains the Round 2 steel-man bundle:
runtime `specs/`, structurally undecided data binding, and a separate `state/`
root (`claude_code/round-2_author-reply.md:92-103`; confirmed at
`codex/round-2_reviewer-reply.md:61-80`). Round 4 adds no new mechanism beyond
repeating the same withdrawal (`claude_code/round-4_author-reply.md:86-100`).
The evidence still points one way: x38 `drafts/`/`published/` belongs to the
design-authoring workflow, not the Alpha-Lab runtime tree
(`x38_RULES.md:33-58`; `PLAN.md:676-692`; `docs/design_brief.md:150-167`), while
the real invariant is checksum-bound snapshot identity at the campaign/data
boundary (`docs/design_brief.md:96-103,179-182`; `PLAN.md:445-447,581-599`).
The only surviving change remains the narrower checksum or manifest reference in
`campaign.json`. `Converged` stands.

## X38-D-13 — Three-identity-axis model

The strongest current opposing claim remains the Round 2 steel-man: without an
immediate bump taxonomy, `protocol_version` risks becoming inert metadata and
Topic 001's one-way invariant risks becoming unenforceable
(`claude_code/round-2_author-reply.md:150-159`; confirmed at
`codex/round-2_reviewer-reply.md:84-113`). Round 4 adds no stronger version of
that argument (`claude_code/round-4_author-reply.md:107-131`).

The mechanism still fails on the same jurisdictional and routing record. Topic
001 already defaults ambiguous or unproven preservation cases to HANDOFF
(`debate/001-campaign-model/final-resolution.md:121-143`), while Topic 001 also
explicitly defers protocol schema to 008, protocol content to 003, and semantic
change classification to 015 (`debate/001-campaign-model/final-resolution.md:164-170`;
`debate/015-artifact-versioning/findings-under-review.md:92-99`). Campaign
lineage is already a required campaign property (`debate/001-campaign-model/final-resolution.md:44-46`),
and Topic 010's same-family consumer need remains a downstream consumer
constraint, not a blocker inside 008
(`debate/010-clean-oos-certification/final-resolution.md:120-123,152-156,176-177`).
`docs/online_vs_offline.md:58-80` still blocks importing gen4 governance
mechanics as an offline template. `Converged` stands.

## X38-SSE-04-IDV — Candidate-level identity vocabulary

The strongest current opposing claim remains the Round 2 steel-man: a unified
4-axis model is needed to prevent downstream fragmentation
(`claude_code/round-2_author-reply.md:202-210`; confirmed at
`codex/round-2_reviewer-reply.md:117-139`). Round 4 does not introduce a
stronger fragmentation mechanism; it only reaffirms the same routed split
(`claude_code/round-4_author-reply.md:135-154`).

That split remains the correct one. Topic 018 still separates field 3
`identity_vocabulary` from field 4 `equivalence_method` and leaves field-3
ownership to downstream synthesis
(`debate/018-search-space-expansion/final-resolution.md:122-155,306-319`).
Topic 013 still owns behavioral thresholds and structural-hash granularity
(`debate/013-convergence-analysis/findings-under-review.md:215-219`), while
Topic 017 still owns phenotype and structural-prior consumption
(`debate/017-epistemic-search-policy/findings-under-review.md:102-165`). That
record defeats the only remaining reason to collapse candidate identity into a
fourth macro axis. `Converged` stands.

## Closure note

No new topic was created. No new issue was added. No false-convergence defect
survives after Round 2's §7(c) confirmations. After this reply, round symmetry
also exists on the straightforward branch of `debate/rules.md:70-75`. Topic 008
remains ready for Prompt C closure, but it is not yet closed on disk until
`final-resolution.md` and the status ledgers are synchronized.

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-D-02 | 3 pillars are sufficient for v1; responsibility mapping remains documentation, not a 4th-boundary argument | Judgment call | Converged | Topic 017 might still expose an ESP invariant forcing pillar promotion | Authority still names exactly 3 mandatory components (`docs/design_brief.md:34-89`, `PLAN.md:663-670`); Topic 017 already allows ESP to fold into Protocol Engine if 008 keeps 3 pillars (`debate/017-epistemic-search-policy/findings-under-review.md:351-353`) |
| X38-D-09 | Directory tree stands; only the campaign-to-data checksum or manifest contract needs tightening | Thiếu sót | Converged | Runtime audit needs `specs/`; data binding is structurally undecided; governance state needs a separate root | x38 `drafts/`/`published/` belongs to design authoring, not Alpha-Lab runtime (`x38_RULES.md:33-58`, `PLAN.md:676-692`); snapshot identity is already the invariant (`docs/design_brief.md:96-103,179-182`, `PLAN.md:445-447,581-599`) |
| X38-D-13 | Add explicit `protocol_version`; campaign lineage remains the `program_lineage_id`-equivalent carrier; defer bump taxonomy to 003/015 | Thiếu sót | Converged | Without immediate taxonomy, `protocol_version` becomes inert metadata and Topic 001's invariant is unenforceable | Topic 001 already defaults ambiguous preservation cases to HANDOFF (`debate/001-campaign-model/final-resolution.md:121-143`); ownership split remains explicit across 008/003/015 (`debate/001-campaign-model/final-resolution.md:164-170`; `debate/015-artifact-versioning/findings-under-review.md:92-99`); campaign lineage is already required (`debate/001-campaign-model/final-resolution.md:44-46`); gen4 governance mechanics are not an offline template (`docs/online_vs_offline.md:58-80`) |
| X38-SSE-04-IDV | Candidate-level identity contract is required alongside D-13, not as a 4th macro axis; 008 owns interface, 013 semantics, 017 consumption | Thiếu sót | Converged | A unified 4-axis model is needed to prevent downstream fragmentation | Topic 018 separates `identity_vocabulary` from `equivalence_method` and routes field-3 ownership downstream (`debate/018-search-space-expansion/final-resolution.md:122-155,306-319`); Topic 013 owns thresholds/granularity (`debate/013-convergence-analysis/findings-under-review.md:215-219`); Topic 017 owns consumption (`debate/017-epistemic-search-policy/findings-under-review.md:102-165`) |
