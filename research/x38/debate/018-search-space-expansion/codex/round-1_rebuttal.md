# Round 1 — Rebuttal: Search-Space Expansion
**Topic**: 018 — Search-Space Expansion
**Author**: codex
**Date**: 2026-03-27
**Responds to**: `claude_code/round-1_opening-critique.md`
**Scope**: SSE-D-01 (Lane ownership), SSE-D-02/03 (Bounded ideation / cold-start),
           SSE-D-04 (Breadth-expansion contract), SSE-D-05 (Surprise lane),
           SSE-D-06 (Cell + equivalence), SSE-D-07 (3-layer lineage),
           SSE-D-08 (Contradiction memory), SSE-D-09 (Multiplicity control),
           SSE-D-10 (Domain-seed hook), SSE-D-11 (APE v1 scope)
**Artifacts read**:
- `AGENTS.md`
- `docs/online_vs_offline.md`
- `x38_RULES.md`
- `PLAN.md`
- `EXECUTION_PLAN.md`
- `docs/design_brief.md`
- `debate/rules.md`
- `debate/prompt_template.md`
- `debate/018-search-space-expansion/README.md`
- `debate/018-search-space-expansion/findings-under-review.md`
- `debate/018-search-space-expansion/claude_code/round-1_opening-critique.md`
- `debate/018-search-space-expansion/final-resolution.md` (non-authoritative input from prior extra-canonical debate)
- `debate/018-search-space-expansion/closure-audit.md` (non-authoritative input from prior extra-canonical debate)
- `docs/search-space-expansion/request.md`
- `debate/002-contamination-firewall/final-resolution.md`
- `debate/003-protocol-engine/findings-under-review.md`
- `debate/004-meta-knowledge/final-resolution.md`
- `debate/006-feature-engine/findings-under-review.md`
- `debate/008-architecture-identity/final-resolution.md`
- `debate/008-architecture-identity/codex/round-1_rebuttal.md`
- `debate/013-convergence-analysis/findings-under-review.md`
- `debate/015-artifact-versioning/findings-under-review.md`
- `debate/017-epistemic-search-policy/findings-under-review.md`

**Mandatory rule reminder**:
1. §4: Attack the argument, not the conclusion.
2. §7: Steel-man is required before marking `Converged`.
3. §8: No soft concession language; every concession must be evidence-backed.
4. §12: No new topic creation after round 1.

Claims below survived a lightweight council on the same disagreement set:
challenger, evidence checker, and rule auditor. I keep every issue `Open`
because `debate/rules.md:30-40` requires Claude's explicit §7(c) confirmation
before any `Converged` mark is valid.

## SSE-D-01 — Lane ownership

**Verdict**: The fold into existing topics survives. Claude's routing-table
amendment is not justified on the current record.

**Classification**: Judgment call

**Evidence pointers**:
- `x38_RULES.md:84-94`
- `debate/018-search-space-expansion/findings-under-review.md:27-31,176-183`
- `debate/015-artifact-versioning/findings-under-review.md:130-141`
- `debate/013-convergence-analysis/findings-under-review.md:157-167`
- `debate/017-epistemic-search-policy/findings-under-review.md:386-446`
- `debate/003-protocol-engine/findings-under-review.md:19-25,75-84`
- `debate/006-feature-engine/findings-under-review.md:11-18,72-77`

**Critique**:

Claude identifies a closure-hygiene concern and mislabels it as an architectural
gap. Under `x38_RULES.md:84-94`, the authoritative unit is the topic directory,
not a synthetic registry layer inside Topic 018. The live record already
materializes several routed SSE obligations in 015, 013, and 017, while 003
and 006 absorb routed work through broader owner-topic findings rather than
SSE-specific issue ledgers. That materially weakens the case for a universal
machine-checkable routing table. Requiring every routed object to appear as a
separate downstream issue or sub-issue would still force artificial
issue-splitting in owner topics whose current findings are intentionally
coarse-grained.

What survives from Claude's point is narrower: directional routing is not
closure authority by itself. That was already corrected in the non-authoritative
018 synthesis. What does not survive is the claim that a universal
"machine-checkable" table is now required. The current x38 governance surface
for orphan risk is primarily the downstream topic ledger plus cross-topic
tensions, even though 003/006 still absorb some routed work through broader
owner-topic findings.

## SSE-D-02 — Bounded ideation

**Verdict**: Replacing SSS with bounded ideation survives. Claude's attempt to
move grammar-provenance policing into `results-blind` does not.

**Classification**: Thiếu sót

**Evidence pointers**:
- `docs/design_brief.md:40-55,84-89`
- `debate/002-contamination-firewall/final-resolution.md:49-77,141-149`
- `debate/004-meta-knowledge/final-resolution.md:189-195,215-223`
- `debate/018-search-space-expansion/findings-under-review.md:44-49`
- `debate/018-search-space-expansion/claude_code/round-1_opening-critique.md:149-180`

**Critique**:

Claude is right that grammar authorship can carry priors. The error is where he
places that concern. `results-blind` is a lane-input rule: what the ideation
agent may see at proposal time. Whether a grammar or operator table is itself
admissible knowledge is a Topic 002 / Topic 004 question governed by the
firewall and MK-17 shadow-only law, not by redefining the ideation lane.

That distinction matters. If a grammar was reverse-engineered from empirical
outcomes on the same dataset, the violation is not "D-02 needs a sharper
definition"; the violation is "002/004 must block or shadow that knowledge."
Claude's amendment therefore attacks the wrong layer. The bounded-ideation
contract should stay narrow: no registry, no prior results, no runtime AI. The
provenance-admissibility problem belongs upstream in the knowledge gate.

## SSE-D-03 — Conditional cold-start

**Verdict**: Conditional cold-start survives. Claude's recap understates the
guard on `registry_only`.

**Classification**: Thiếu sót

**Evidence pointers**:
- `debate/018-search-space-expansion/findings-under-review.md:44-49`
- `debate/018-search-space-expansion/final-resolution.md:104-110,233-236`
- `debate/018-search-space-expansion/claude_code/round-1_opening-critique.md:137-142`

**Critique**:

The current record does not support treating `registry_only` as merely "import a
frozen non-empty registry." The non-authoritative 018 synthesis already locked a
stronger protocol-lock guard: registry non-empty, frozen, and
`grammar_hash`-compatible. Claude's opening retains the first two conditions and
drops the third.

That omission matters because the live architectural dispute is not mandatory
versus optional capability anymore. It is protocol-lock validation. A
`registry_only` path without grammar-compatibility checking would permit silent
warm-start drift. So the surviving rebuttal point is narrower than Claude's
amendment: keep the conditional cold-start law, but do not dilute its lock-time
guard.

## SSE-D-04 — Breadth-expansion contract

**Verdict**: The 7-field contract survives. Claude's owner-gap amendment for
field 3 is overtaken by the current record.

**Classification**: Thiếu sót

**Evidence pointers**:
- `debate/018-search-space-expansion/claude_code/round-1_opening-critique.md:217-231`
- `debate/008-architecture-identity/final-resolution.md:4,14-15,131-140`
- `EXECUTION_PLAN.md:31-32`
- `debate/013-convergence-analysis/findings-under-review.md:148-149,215-219`
- `debate/017-epistemic-search-policy/findings-under-review.md:430-435`
- `x38_RULES.md:84-94`

**Critique**:

Claude's opening is built on a provisional 018 note that said field 3 owner
assignment was still `TBD`. Topic 008 has now closed on 2026-03-27 and
substantially narrows that gap by assigning the split provisionally: 008 owns
the existence obligation and structural pre-bucket fields, 013 owns
equivalence semantics, and 017 owns consumption.

Because `x38_RULES.md:84-94` makes the topic directory authoritative, the
owner-gap concern is now substantially narrowed. The remaining live question is
whether Topic 018 will sync to the now-closed 008 decision when 018 re-closes.
Claude's orphan warning therefore overshoots. What remains open downstream are
semantic thresholds and consumption details, not a blank owner field.

## SSE-D-05 — Surprise lane

**Verdict**: The minimum recognition inventory survives. Claude's rationale
leans too hard on one motivating anecdote.

**Classification**: Thiếu sót

**Evidence pointers**:
- `debate/018-search-space-expansion/findings-under-review.md:62-66`
- `debate/017-epistemic-search-policy/findings-under-review.md:426-446`
- `docs/design_brief.md:27-30,63-74`

**Critique**:

VDO is a valid motivation for "peak score is not enough." It is not sufficient
evidence, by itself, to prove this exact five-axis / five-component minimum.
The design survives for a narrower reason: Topic 018 locks a minimum
non-peak-score admission/proof contract while explicitly deferring numeric
thresholds and exact taxonomy values to 017/013.

So the correct argument is obligation-level, not anecdote-level. Claude reaches
the right design surface and overstates the proof.

## SSE-D-06 — Hybrid equivalence

**Verdict**: Hybrid equivalence survives. Claude overstates how much the issue
is finished.

**Classification**: Thiếu sót

**Evidence pointers**:
- `debate/008-architecture-identity/final-resolution.md:135-140`
- `debate/013-convergence-analysis/findings-under-review.md:212-219,225-228`
- `debate/015-artifact-versioning/findings-under-review.md:223-227`
- `debate/018-search-space-expansion/findings-under-review.md:137-139`

**Critique**:

The current record is strong enough to reject AST-only. But the stronger reason
is not merely that Gemini withdrew in a prior extra-canonical debate. The
stronger reason is that the cross-topic split is now explicit: 008 owns the
structural pre-bucket contract, 013 owns behavioral thresholds and hash
granularity, and 015 still owns invalidation behavior when taxonomy/domain/cost
assumptions change.

That means hybrid equivalence is versioned determinism, not context-free
determinism. Claude's conclusion survives; his "concern addressed" language is
too final for a record where thresholds and invalidation are still open
downstream.

## SSE-D-07 — 3-layer lineage

**Verdict**: The semantic split survives and remains routed to 015.

**Classification**: Thiếu sót

**Evidence pointers**:
- `debate/018-search-space-expansion/findings-under-review.md:80-81`
- `debate/015-artifact-versioning/findings-under-review.md:145-176`

**Critique**:

There is no substantive architectural rebuttal left in Claude's section. Topic
015 already carries the exact open work: field enumeration, invalidation matrix,
and raw-lineage preservation. That means the surviving 018 claim is narrow:
`feature_lineage`, `candidate_genealogy`, and `proposal_provenance` are
different semantic objects. The rest is now 015 implementation detail.

The issue stays `Open` only because §7 has not completed in this canonical
re-debate, not because Claude identified a fresh mechanism dispute here.

## SSE-D-08 — Contradiction memory

**Verdict**: Shadow-only contradiction storage survives. Claude's
queue-priority carveout is not proven compatible with MK-17.

**Classification**: Judgment call

**Evidence pointers**:
- `docs/design_brief.md:84-89,107-118`
- `debate/004-meta-knowledge/final-resolution.md:191-195,215-223`
- `debate/017-epistemic-search-policy/findings-under-review.md:145-162,213-218`
- `debate/017-epistemic-search-policy/findings-under-review.md:274-313,327-328`
- `debate/017-epistemic-search-policy/findings-under-review.md:396-412`
- `debate/018-search-space-expansion/claude_code/round-1_opening-critique.md:349-380`

**Critique**:

Claude is correct that the interaction must be made explicit. He has not proved
his proposed resolution. The live 017 record defines same-dataset structural
priors as `SHADOW` only and treats `ORDER_ONLY` / `BUDGET_ONLY` as active
scopes. His carveout says contradiction resurrection may influence queue
priority while remaining MK-17-compliant. That is not reconciled by the current
record. At minimum, he must show why surprise-queue priority is not an active
influence of the same kind 017 already treats cautiously.

So the strongest surviving position is narrower than Claude's probe: there is a
real unresolved mechanism dispute at the 017 interface. What does not survive
is the claim that "queue-priority only" already solves it.

## SSE-D-09 — Multiplicity control

**Verdict**: Breadth coupling to multiplicity control survives.

**Classification**: Thiếu sót

**Evidence pointers**:
- `debate/003-protocol-engine/findings-under-review.md:65-71`
- `debate/013-convergence-analysis/findings-under-review.md:171-199`
- `debate/018-search-space-expansion/findings-under-review.md:153-154`

**Critique**:

The architectural claim is now straightforward. Topic 003 already records the
scan-phase multiple-testing problem at Stage 3; Topic 013 already owns the
routed default-law debate. That is enough to justify the breadth-activation
requirement to declare a correction method before expansion.

What remains open is formula selection, not whether multiplicity belongs in the
gate at all. Claude's section is directionally right and does not move the
design surface.

## SSE-D-10 — Domain-seed hook

**Verdict**: V1 remains an optional provenance hook. Stronger runtime semantics
still lack evidence.

**Classification**: Judgment call

**Evidence pointers**:
- `debate/018-search-space-expansion/findings-under-review.md:123-124`
- `docs/online_vs_offline.md:71-82`
- `docs/design_brief.md:24-30,78-89`

**Critique**:

Claude reaches the right boundary. The stronger reason is not merely "minimal
infrastructure for v1." The stronger reason is that replay semantics, domain
catalogs, or session formats would start importing online-style authoring
machinery into an offline pipeline without a source-backed need.

The only surviving v1 law is provenance preservation. Anything beyond that is a
future proposal, not a current architectural requirement.

## SSE-D-11 — APE v1 scope

**Verdict**: V1 remains template parameterization only.

**Classification**: Thiếu sót

**Evidence pointers**:
- `docs/online_vs_offline.md:25-36,44-54`
- `docs/design_brief.md:51-55,63-74`
- `debate/018-search-space-expansion/findings-under-review.md:167-168`

**Critique**:

Claude is right to keep free-form code generation out of v1. The narrower
reason is that v1 only has auditable, bounded generation surfaces. Human-authored
templates plus parameter bounds keep output inside the existing validation,
freeze, and firewall model. Arbitrary generated code would bypass that model
before 003/006/015 have any correctness or invalidation contract to govern it.

So the surviving argument is "bounded, auditable generation only," not merely
"type-checking is easy."

## What survives from the opening critique

Four issues still matter at design level:

1. `SSE-D-01`: no Topic 018 umbrella for substance remains the right boundary,
   but the proposed routing-table cure is not shown to be necessary on the
   current record and would duplicate tracking for several already-materialized
   routed obligations.
2. `SSE-D-02/03`: bounded ideation + conditional cold-start survive, but the
   real open boundary is topic ownership for provenance/admissibility and the
   exact protocol-lock guard on `registry_only`.
3. `SSE-D-04`: the 7-field contract survives, while the field-3 owner-gap claim
   is overtaken by Topic 008's closure on 2026-03-27.
4. `SSE-D-08`: contradiction consumption still needs explicit 017 law; Claude's
   queue-priority carveout has not yet carried that burden.

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| SSE-D-01 | Fold substance into 006/015/017/013/008/003; no umbrella topic | Judgment call | Open | "Without mirrored downstream issue IDs, the fold is only a slogan." | Several routed SSE obligations already exist where granularity requires them; 003/006 still absorb some routed work through broader owner-topic findings. |
| SSE-D-02 | Keep bounded ideation narrow; do not move grammar-admissibility policing into `results-blind` | Thiếu sót | Open | "Grammar can encode prior outcomes, so D-02 must define admissibility of grammar provenance." | That is a 002/004 firewall and MK-17 question, not an ideation-lane input contract. |
| SSE-D-03 | Keep conditional cold-start and preserve strong `registry_only` lock-time guard | Thiếu sót | Open | "`registry_only` is just a shortcut for any non-empty frozen registry." | The current record also requires `grammar_hash` compatibility; otherwise warm-start drift is ungoverned. |
| SSE-D-04 | Keep the 7-field contract; sync field 3 to the now-closed 008 decision | Thiếu sót | Open | "Field 3 remains orphaned until 018 reassigns ownership." | Topic 008 now provisionally assigns the split: 008 interface, 013 semantics, 017 consumption; 018 needs to sync to that on re-closure. |
| SSE-D-05 | Keep minimum anomaly/proof inventory as obligation-level floor | Thiếu sót | Open | "One VDO-style anecdote is too thin to justify this exact minimum bundle." | 018 locks only a minimum inventory; thresholds and exact categories remain downstream. |
| SSE-D-06 | Keep hybrid equivalence as versioned deterministic contract | Thiếu sót | Open | "AST-only stability outweighs behavioral dependence." | 008/013 split plus explicit invalidation handling is stronger than AST-only and still deterministic. |
| SSE-D-07 | Keep the 3-layer semantic split routed to 015 | Thiếu sót | Open | "Without exact fields, the issue cannot leave 018." | 015 already owns exact fields and invalidation; 018 only needs the semantic split. |
| SSE-D-08 | Keep shadow-only contradiction storage; do not treat queue-priority carveout as already validated | Judgment call | Open | "Queue-priority only does not affect scores, so it stays within MK-17." | The current 017 record has not reconciled queue priority with same-dataset `SHADOW`-only scope. |
| SSE-D-09 | Keep multiplicity coupling in the breadth gate and route formula choice to 013 | Thiếu sót | Open | "Until Holm/BH/cascade is chosen, breadth should not require a declared correction method." | The gate needs declared correction ownership before expansion; exact formula remains a downstream choice. |
| SSE-D-10 | Keep domain-seed as optional provenance hook only | Judgment call | Open | "A provenance-only hook is too weak; v1 needs domain replay semantics now." | The current record supports authoring provenance only; stronger runtime machinery is not source-backed. |
| SSE-D-11 | Keep APE v1 at template parameterization only | Thiếu sót | Open | "Free-form code generation is required for real structural innovation." | V1 only has bounded, auditable generation surfaces; arbitrary generated code escapes current correctness and firewall contracts. |
