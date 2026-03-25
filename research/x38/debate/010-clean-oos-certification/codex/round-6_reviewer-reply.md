# Round 6 — Reviewer Reply: Clean OOS & Certification
**Topic**: 010 — Clean OOS & Certification
**Author**: codex
**Date**: 2026-03-25
**Responds to**: `claude_code/round-6_author-reply.md`
**Scope**: X38-D-12, X38-D-21, X38-D-23, X38-D-24
**Artifacts read**:
- `AGENTS.md`
- `docs/online_vs_offline.md`
- `x38_RULES.md`
- `debate/rules.md`
- `debate/prompt_template.md`
- `debate/010-clean-oos-certification/README.md`
- `debate/010-clean-oos-certification/findings-under-review.md`
- `debate/010-clean-oos-certification/claude_code/round-6_author-reply.md`
- `debate/010-clean-oos-certification/codex/round-5_reviewer-reply.md`
- `debate/010-clean-oos-certification/claude_code/round-5_author-reply.md`
- `debate/010-clean-oos-certification/claude_code/round-4_author-reply.md`
- `debate/010-clean-oos-certification/codex/round-4_reviewer-reply.md`
- `debate/010-clean-oos-certification/claude_code/round-3_author-reply.md`
- `debate/010-clean-oos-certification/codex/round-3_reviewer-reply.md`
- `debate/010-clean-oos-certification/claude_code/round-2_author-reply.md`
- `debate/010-clean-oos-certification/codex/round-2_reviewer-reply.md`
- `debate/010-clean-oos-certification/claude_code/round-1_opening-critique.md`
- `debate/010-clean-oos-certification/codex/round-1_rebuttal.md`
- `docs/design_brief.md`
- `PLAN.md`
- `drafts/architecture_spec.md`
- `debate/007-philosophy-mission/final-resolution.md`
- `debate/008-architecture-identity/findings-under-review.md`
- `debate/004-meta-knowledge/final-resolution.md`

**MANDATORY RULE REMINDER:**
1. §4: Attack the argument, not the conclusion.
2. §7: Steel-man is required before marking `Converged`.
3. §8: No soft concession language; every concession must be evidence-backed.
4. §12: No new topic creation after round 1.

Challenger, evidence check, and rule audit were applied on the same disagreement
set before synthesis. After those checks, the narrowed Round 6 picture is:
X38-D-21 now has an explicit repair for the last live governance gap; X38-D-12
can therefore close with it; X38-D-24 remains converged; X38-D-23 is narrower
than before but still not fully settled inside this round artifact.

## X38-D-21: CLEAN_OOS_INCONCLUSIVE

Your Round 6 steel-man is accurate. My strongest remaining `Open` position after
Round 5 was not reserve overlap or automatic count-based `FAIL`. Those disputes
were already narrowed away in Round 4 and Round 5. The surviving objection was
the smaller governance gap: the canonical texts freeze only the initial
`PENDING_CLEAN_OOS` trigger and the no-silent-deferral rule, but they did not
yet expressly freeze post-`INCONCLUSIVE` re-fire semantics
(`docs/design_brief.md:132-145`; `PLAN.md:463-474,519-528`;
`debate/010-clean-oos-certification/findings-under-review.md:125-128`;
`codex/round-5_reviewer-reply.md:77-96`).

That steel-man no longer holds once your Round 6 reply adds the missing clause
explicitly. I do **not** accept the stronger claim that older canonical text had
already frozen stateless re-triggering. The evidence check is right that this is
an inference plus a new explicit freeze, not something the older sources said on
their own. But Prompt B asks me to answer the strongest current argument, and
the current argument now supplies exactly the contract my Round 5 objection said
was missing: after an `INCONCLUSIVE`, the already-accepted Reserve Rollover
Invariant moves the clean-OOS boundary to the prior `reserve_end_*`, and
`PENDING_CLEAN_OOS` is then evaluated again against elapsed data from that new
boundary (`claude_code/round-4_author-reply.md:172-193`;
`codex/round-4_reviewer-reply.md:67-85`;
`claude_code/round-6_author-reply.md:61-108`).

With that explicit repair in place, F-21's remaining open bullet is answered
without reopening rejected mechanisms. `INCONCLUSIVE` still does not
auto-convert to `FAIL`, because D-24 already froze honest underpower labeling
(`codex/round-3_reviewer-reply.md:144-151`). Human judgment happens at every
re-fired `PENDING_CLEAN_OOS` review under the existing explicit-deferral /
no-silent-delay rule (`docs/design_brief.md:133-136`; `PLAN.md:470-474`).

I therefore confirm §7(c): yes, your Round 6 steel-man states my strongest
remaining objection, and the new explicit trigger semantics defeat it on the
merits. X38-D-21 is `Converged`.

## X38-D-12: Clean OOS via future data

Your Round 6 narrowing is also accurate. My surviving D-12 objection after
Round 5 was no longer about the consumed-reserve-slice schema, FAIL provenance
placement, D-24's method-first minimum-duration answer, or Topic 003 pipeline
ownership. It was the narrower F-12 line-77 dependency: D-12 could not close
while the short-data branch still ran through unresolved D-21 governance
(`debate/010-clean-oos-certification/findings-under-review.md:74-83`;
`codex/round-5_reviewer-reply.md:33-56`).

That steel-man no longer holds because D-21 now has the explicit rerun rule it
lacked. Underpowered reserve -> `INCONCLUSIVE` -> keep
`INTERNAL_ROBUST_CANDIDATE` -> re-fire `PENDING_CLEAN_OOS` from a later
non-overlapping clean slice is now a closed path, not a placeholder
(`docs/design_brief.md:120-145`; `PLAN.md:519-543`;
`claude_code/round-6_author-reply.md:133-165`).

The rest of D-12's load was already discharged earlier: Round 4 repaired the
consumed-reserve-slice recording gap, D-24 froze the method-first minimum-power
law, and Topic 010's own cross-topic ledger routes pipeline placement to Topic
003 (`codex/round-4_reviewer-reply.md:43-62`;
`debate/010-clean-oos-certification/findings-under-review.md:244`).

I therefore confirm §7(c) here as well: your dependency framing states the
strongest remaining objection, and that objection fails now that D-21's rerun
governance is explicit. X38-D-12 is `Converged`.

## X38-D-23: Pre-existing candidates vs x38 winners

Your Round 6 reply correctly narrows the field. I do not reopen contradiction
symmetry, single-artifact demands, or the claim that Scenario 1 is already
fully frozen without identity work. The accepted ground is now:
- Scenario 2 contradiction is already covered by Topic 007's below-certification
  MUST-surface rule (`debate/007-philosophy-mission/final-resolution.md:90-95`).
- Same-dataset pre-existing candidates remain shadow-only provenance, not active
  ranking input (`docs/design_brief.md:87-89`;
  `drafts/architecture_spec.md:39-40`).
- Clean OOS certifies x38's own frozen winner, not the pre-existing candidate
  by default (`drafts/architecture_spec.md:140-145`;
  `debate/010-clean-oos-certification/findings-under-review.md:156-162`).

But D-23 still does not fully converge in this round artifact.

For Scenario 1, your evidence is sufficient to show that family identity cannot
be silently assumed. Your own Round 2 reply already conceded that the
same-family comparison depends on unresolved identity work outside the original
opening proposal (`claude_code/round-2_author-reply.md:117-124`), and Topic 008
still keeps identity schema open (`debate/008-architecture-identity/findings-under-review.md:120-159`).
That defeats any stale claim that Scenario 1 is already operationally frozen.
But it does **not** yet prove the stronger boundary claim that Topic 010 needs
no additional relation / lookup contract once identity is available. Topic 007
left that surface open for consuming topics rather than freezing it away
(`debate/007-philosophy-mission/final-resolution.md:94-95`).

Scenario 3 remains in the same zone. Your proposed null-state invariant is
coherent, but it is still a proposal, not a source-frozen x38 contract.
`NO_ROBUST_IMPROVEMENT` records only "no x38 winner"
(`drafts/architecture_spec.md:136-145`), while F-23 still treats the
pre-existing-candidate / no-winner combination as a distinct open case
(`debate/010-clean-oos-certification/findings-under-review.md:151-173`).
Whether Topic 010 may leave that state derivable from provenance, or must freeze
an explicit below-certification lookup / surfacing contract, remains a real
closure-boundary dispute.

So the residual disagreement is now narrower than a mechanism fight over
contradiction handling. It is a completeness / boundary dispute that closure
must handle under §14, with `decision_owner = human researcher`:
- Claude Code position: Topic 010 is complete once shadow-only provenance,
  contradiction surfacing, and x38-only certification are frozen; Scenario 1
  waits on identity work, and Scenario 3 is derivable.
- Codex position: Topic 010 should still freeze the below-certification relation
  / lookup contract for Scenario 1 and the Scenario 3 null state before topic
  closure.

For this Round 6 Prompt-B artifact, X38-D-23 stays `Open`.

## X38-D-24: Clean OOS power rules

No live mechanism dispute remains. The converged v1 contract is still the
method-first rule frozen in Round 3 and affirmed in Round 4 and Round 5:
predeclared campaign-specific power method; calendar-time and trade-count
criteria mandatory at minimum; honest `INCONCLUSIVE` when that method says the
reserve is underpowered; additional dimensions method-dependent rather than
universal v1 gates (`codex/round-3_reviewer-reply.md:144-157`;
`codex/round-4_reviewer-reply.md:120-129`;
`codex/round-5_reviewer-reply.md:143-153`;
`claude_code/round-5_author-reply.md:191-194`).

The only remaining mismatch is ledger sync: `findings-under-review.md` still
records X38-D-24 as `Open`. That is a closure bookkeeping task, not a live
debate mechanism. X38-D-24 remains `Converged`.

## §14 Note

Round parity is now satisfied for Topic 010. In this round artifact,
X38-D-12, X38-D-21, and X38-D-24 are converged on evidence-backed grounds.
X38-D-23 is the only issue still `Open`, and the tradeoff that closure must
carry into §14 is stated above without prematurely converting the round file
itself into Prompt C.

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-D-12 | D-12's remaining short-data dependency is now closed through explicit D-21 rerun governance; earlier schema/power/pipeline submechanisms were already discharged | Judgment call | Converged | F-12 line-77 stayed unresolved while D-21 lacked an explicit path from `INCONCLUSIVE` back to later Clean OOS review | Round 6 now makes that path explicit: `INCONCLUSIVE` preserves `INTERNAL_ROBUST_CANDIDATE`, rollover moves the boundary, and `PENDING_CLEAN_OOS` re-fires from the new clean slice (`findings-under-review.md:74-83`; `claude_code/round-6_author-reply.md:77-108,153-165`) |
| X38-D-21 | Explicit re-trigger semantics close the last repeated-`INCONCLUSIVE` governance gap without reopening auto-`FAIL` or overlap disputes | Thiếu sót | Converged | The design froze initial trigger + no-silent-deferral, but not post-`INCONCLUSIVE` re-fire semantics | The strongest remaining objection fails because Round 6 adds the missing clause tying `PENDING_CLEAN_OOS` to elapsed data since the rolled-over boundary; D-24 still blocks count-based `FAIL`, and existing review governance now applies on each trigger (`docs/design_brief.md:133-136`; `PLAN.md:470-474`; `claude_code/round-6_author-reply.md:77-108`) |
| X38-D-23 | Contradiction handling, shadow-only provenance, and x38-only certification are settled; the remaining dispute is whether Scenario 1 / Scenario 3 need an explicit below-certification relation contract before topic closure | Thiếu sót | Open | Shadow-only provenance plus campaign verdict already make Scenario 1 / Scenario 3 complete without any further contract | Evidence defeats stale stronger claims, but it still does not settle the closure-boundary question: Topic 008 leaves identity work open, and Scenario 3's null-state rule is still proposed rather than frozen (`claude_code/round-2_author-reply.md:117-124`; `debate/008-architecture-identity/findings-under-review.md:120-159`; `findings-under-review.md:151-173`) |
| X38-D-24 | Method-first power law remains the settled v1 contract; only ledger sync is left | Thiếu sót | Converged | Topic 010 could not converge until it froze one stronger universal binding dimension set or exact derivation law directly | That objection failed in Round 3 once the contract narrowed to predeclared method + mandatory calendar/trade-count criteria + honest underpower labeling, not a universal gate set (`codex/round-3_reviewer-reply.md:144-157`) |
