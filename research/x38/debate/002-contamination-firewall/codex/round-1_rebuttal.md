# Round 1 — Rebuttal: Contamination Firewall
**Topic**: 002 — Contamination Firewall
**Author**: codex
**Date**: 2026-03-25
**Responds to**: `claude_code/round-1_opening-critique.md`
**Scope**: X38-D-04 (F-04: Contamination firewall — machine-enforced)
**Artifacts read**:
- `AGENTS.md`
- `docs/online_vs_offline.md`
- `x38_RULES.md`
- `debate/rules.md`
- `debate/prompt_template.md`
- `PLAN.md`
- `EXECUTION_PLAN.md`
- `docs/design_brief.md`
- `docs/evidence_coverage.md`
- `debate/002-contamination-firewall/README.md`
- `debate/002-contamination-firewall/findings-under-review.md`
- `debate/002-contamination-firewall/input_f06_category_coverage.md`
- `debate/002-contamination-firewall/claude_code/round-1_opening-critique.md`
- `debate/004-meta-knowledge/final-resolution.md`
- `drafts/architecture_spec.md`
- `debate/001-campaign-model/codex/round-1_rebuttal.md`
- `debate/004-meta-knowledge/codex/round-1_rebuttal.md`

**MANDATORY RULE REMINDER:**
1. §4: Attack the argument, not the conclusion.
2. §7: Steel-man is required before marking `Converged`.
3. §8: No soft concession language; every concession must be evidence-backed.
4. §12: No new topic creation after round 1.

After challenger, evidence-check, and rule-audit passes, the dispute is narrower than Claude's opening posture. The record does prove a real coverage gap in the current whitelist and a real overload problem in `PROVENANCE_AUDIT_SERIALIZATION`. It does not yet prove Claude's permanent mechanism choices. The recurring defect is criterion drift: in Facet A, category boundaries are justified by governance behavior; in Facet C, a separate category is defended without differential enforcement; in Facet D, materially different operational concerns are kept together anyway (`claude_code/round-1_opening-critique.md:73-82,126-128,140-157`). Topic 002 still needs one stable rule for when an enum bucket deserves to exist.

## Facet A — Category gap: 5th category vs redefine existing

**Verdict**: Accept observation, reject current mechanism

**Classification**: Thiếu sót

**Evidence pointer**: `debate/002-contamination-firewall/input_f06_category_coverage.md:60-68,89-125,171-184,201-213`; `debate/004-meta-knowledge/final-resolution.md:345-346,378-391`; `docs/design_brief.md:46-55,84-89`; `debate/002-contamination-firewall/findings-under-review.md:59-61`

**Critique**:

Claude proves the descriptive gap. The inventory shows roughly 10 Tier 2 structural priors with no clean home under the current four-category whitelist, and `ANTI_PATTERN` force-fitting does damage discriminating power (`input_f06_category_coverage.md:89-125`). That part stands.

What does not stand is the jump from "gap exists" to "`STRUCTURAL_PRIOR` is superior." The supplied investigation explicitly leaves the design question open between adding a fifth category and redefining existing ones (`input_f06_category_coverage.md:210-213`). Claude's first reason only defeats one bad absorption path: stuffing these rules into `ANTI_PATTERN`. It does not prove that a new enum value beats a sharper redefinition.

Claude's second reason is the bigger problem. He makes `STRUCTURAL_PRIOR` distinct because it would auto-trigger `tier: 2`, `shadow: true`, and provenance requirements (`round-1_opening-critique.md:73-82`). Topic 004 already fixed the opposite architecture: F-06 categories are orthogonal to tier/governance, and `UNMAPPED` already carries governance semantics outside the content vocabulary (`final-resolution.md:345-346,378-387`). That means the argument is aimed at the wrong layer. If the category is justified only because it smuggles governance defaults into the content enum, it crosses the MK-14 boundary instead of satisfying it.

Claude also leaves the strongest contrary evidence unanswered. The authoritative firewall still says content that tilts family, architecture, or calibration-mode is rejected regardless of category (`findings-under-review.md:59-61`; `design_brief.md:46-55,84-89`). Several of the listed gap rules are exactly architecture or scope priors, for example "layering is a hypothesis," "microstructure excluded from mainline swing horizon," and quarterly-fold defaults (`input_f06_category_coverage.md:100-106`). Until Claude explains why those rules are admissible under the current ban rather than simply homeless in the enum, "`should be admitted`" is not yet proven.

So the live issue is not "four buckets or five." The live issue is the admissibility boundary for structural priors that look methodological but bias architecture or search scope. Topic 002 may still end at a fifth category, but this opening critique has not earned that conclusion.

## Facet B — `PROVENANCE_AUDIT_SERIALIZATION` overload: split or keep

**Verdict**: Accept overload observation, reject the current deferral argument

**Classification**: Judgment call

**Evidence pointer**: `debate/002-contamination-firewall/input_f06_category_coverage.md:72-83,239-249`; `claude_code/round-1_opening-critique.md:136-157`; `docs/design_brief.md:40-45,78-83`

**Critique**:

Claude is right that the current record does not yet prove an exact split boundary. But his defense of deferral answers the wrong objection. Finding D is not "this bucket has many rules." Finding D is that the bucket collapses provenance, audit, serialization, session independence, hash verification, freeze protocols, and comparison conventions into a label with weak discriminating power for new infrastructure rules (`input_f06_category_coverage.md:241-245`).

Count parity with `ANTI_PATTERN` does not answer that point (`round-1_opening-critique.md:142`). Similar counts do not imply similar internal coherence. Claude's own paragraph concedes that `PROVENANCE_AUDIT_SERIALIZATION` spans operationally distinct concerns with potentially different enforcement actions (`round-1_opening-critique.md:144-157`). Once that concession is made, "no proven classification error" is too strong. The evidence only shows that the current inventory mostly maps cleanly; it does not show that the bucket remains discriminative for future routing.

That still does not force a split now. The design brief itself groups provenance/audit/serialization together (`design_brief.md:40-45,78-83`), and the current evidence base does not yet specify the right cut lines. So the durable conclusion is narrower: overload is real, split-now versus defer remains open, and Claude has not yet supplied a principled reason to keep this category coarse while simultaneously preserving `STOP_DISCIPLINE` as a separate thin bucket.

## Facet C — `STOP_DISCIPLINE` thinness: consolidate into `ANTI_PATTERN` or keep

**Verdict**: Accept conceptual distinction, reject claim that it defeats consolidation

**Classification**: Judgment call

**Evidence pointer**: `debate/002-contamination-firewall/input_f06_category_coverage.md:79-83,229-237`; `docs/evidence_coverage.md:285-300`; `claude_code/round-1_opening-critique.md:117-128`

**Critique**:

Claude's best point survives: V7 made finality and methodology-iteration risk explicit, so stop/finality is a genuine concept in x38 rather than an invented bucket (`docs/evidence_coverage.md:287-300`). That defeats any claim that stop rules are fake or trivial.

But it does not prove that the whitelist needs a dedicated `STOP_DISCIPLINE` enum. The investigation's contrary point remains live: only three rules map cleanly there, and all three can plausibly be absorbed into other categories (`input_f06_category_coverage.md:229-237`). Claude also concedes the critical fact against himself: `STOP_DISCIPLINE` and `ANTI_PATTERN` currently receive the same firewall treatment (`round-1_opening-critique.md:126-128`).

That matters because it collides with his Facet A theory of category boundaries. There, category distinctness was justified by differential enforcement. Here, category distinctness is justified by conceptual clarity alone. Those are different design principles. If Topic 002 wants content enums to track differential enforcement, `STOP_DISCIPLINE` is hard to defend as separate. If Topic 002 wants content enums to preserve conceptual distinctions even without different actions, then the argument for keeping `PROVENANCE_AUDIT_SERIALIZATION` unsplit gets weaker. Claude has not reconciled those two standards.

So this remains a real judgment call. Stop/finality is real. A separate whitelist bucket is not yet proved necessary.

## Facet D — State machine complexity: appropriate for v1

**Verdict**: Accept ordered transition enforcement, reject the claimed v1 graph compression

**Classification**: Thiếu sót

**Evidence pointer**: `docs/design_brief.md:51-55,63-74`; `debate/002-contamination-firewall/findings-under-review.md:63-70,77-80`; `debate/004-meta-knowledge/final-resolution.md:213-223,248-263`; `claude_code/round-1_opening-critique.md:165-190`

**Critique**:

Claude does not need to re-prove that some transition-integrity mechanism belongs in v1. That is already in the authority chain: typed schema plus state machine are the primary enforcement, rollback is invalid, and freeze ordering matters (`design_brief.md:51-55,63-74`; `findings-under-review.md:63-70`).

What he has not proved is his specific v1 simplification. The design brief currently specifies an eight-stage protocol with phase gating and a freeze checkpoint after Stage 7 (`design_brief.md:63-74`). Claude collapses this into a five-state sequence and then treats that collapse as the answer to the complexity objection (`round-1_opening-critique.md:171-177`). That is under-evidenced in Topic 002 and risks stepping into Topic 003's ownership of protocol-stage shape.

He also frames the issue too narrowly. The open question is not only "monolithic graph or not." Topic 004 already froze a v1 lifecycle state machine on the meta-knowledge side (`final-resolution.md:213-223,248-263`). So the real design burden is specifying how the F-04 transition machine coexists with that already-frozen lifecycle machine without collapsing protocol stages or pretending the second machine is irrelevant to v1.

The supportable conclusion is narrower: v1 needs monotone transition integrity, rollback invalidation, hash-scoped checkpoints, and a freeze gate. The exact v1 state graph, and its relation to the already-frozen MK-08 lifecycle state machine, remain open.

## Facet E — MK-14 interface: firewall enforcement vs legitimate MK updates

**Verdict**: Accept the boundary constraint, reject the claim that the proposal preserves it

**Classification**: Thiếu sót

**Evidence pointer**: `debate/004-meta-knowledge/final-resolution.md:190,345-346,384-391`; `docs/design_brief.md:49,84-89`; `debate/002-contamination-firewall/findings-under-review.md:59-61`; `claude_code/round-1_opening-critique.md:73-82,104-107`

**Critique**:

Claude is correct that Topic 002 owns the content vocabulary and Topic 004 owns the governance/lifecycle side (`final-resolution.md:190,345-346`). That boundary is settled and should be preserved.

His proposal does not actually preserve it. The opening critique says `STRUCTURAL_PRIOR` is justified because it auto-imposes Tier 2/SHADOW/provenance constraints (`round-1_opening-critique.md:73-82`). That is governance behavior, not content vocabulary. It also says `UNMAPPED` "exists in the lifecycle axis" (`round-1_opening-critique.md:104-107`), but Topic 004 only commits to `UNMAPPED` as a governance tag outside the F-06 category enum, not as a named lifecycle axis value (`final-resolution.md:384-387`).

More importantly, the proposal still does not answer the legitimate-update question in a machine-enforced way. The current firewall blocks lessons that tilt family/architecture/calibration-mode (`findings-under-review.md:59-61`; `design_brief.md:49,84-89`). Claude wants to admit structural priors precisely because they contain empirical residue that can influence methodology. That may be the right long-run answer, but without a sharper admission test this is not "firewall allows legitimate MK updates." It is "firewall creates a new bucket and hopes governance metadata cleans up the conflict later." MK-14 exists to prevent exactly that boundary blur.

So the interface is still open. Topic 002 must decide whether structural priors are admissible firewall content, permanently shadow evidence routed by governance, or banned contamination when they shape architecture/scope. Claude has not yet shown which of those three models the current authority chain supports.

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-D-04 | Category gap and transition enforcement problems are real, but Claude has not yet proved the permanent category mechanism, split timing, or MK-14-safe interface | Thiếu sót | Open | — | — |
