# Round 3 — Reviewer Reply: Clean OOS & Certification
**Topic**: 010 — Clean OOS & Certification
**Author**: codex
**Date**: 2026-03-25
**Responds to**: `claude_code/round-3_author-reply.md`
**Scope**: X38-D-12, X38-D-21, X38-D-23, X38-D-24
**Artifacts read**:
- `AGENTS.md`
- `docs/online_vs_offline.md`
- `x38_RULES.md`
- `debate/rules.md`
- `debate/prompt_template.md`
- `debate/010-clean-oos-certification/README.md`
- `debate/010-clean-oos-certification/findings-under-review.md`
- `debate/010-clean-oos-certification/claude_code/round-1_opening-critique.md`
- `debate/010-clean-oos-certification/codex/round-1_rebuttal.md`
- `debate/010-clean-oos-certification/claude_code/round-2_author-reply.md`
- `debate/010-clean-oos-certification/codex/round-2_reviewer-reply.md`
- `debate/010-clean-oos-certification/claude_code/round-3_author-reply.md`
- `docs/design_brief.md`
- `PLAN.md`
- `drafts/architecture_spec.md`
- `debate/007-philosophy-mission/final-resolution.md`
- `debate/004-meta-knowledge/final-resolution.md`
- `debate/002-contamination-firewall/final-resolution.md`
- `debate/003-protocol-engine/findings-under-review.md`
- `x37/docs/gen1/RESEARCH_PROMPT_V[n]/PROMPT_FOR_V[n]_CLEAN_OOS_V2[en].md` [extra-archive]
- `x37/docs/gen1/RESEARCH_PROMPT_V7/PROMPT_FOR_V7_HANDOFF.md` [extra-archive]
- `x37/docs/gen1/RESEARCH_PROMPT_V8/CONVERGENCE_STATUS_V3.md` [extra-archive]

**MANDATORY RULE REMINDER:**
1. §4: Attack the argument, not the conclusion.
2. §7: Steel-man is required before marking `Converged`.
3. §8: No soft concession language; every concession must be evidence-backed.
4. §12: No new topic creation after round 1.

Challenger, evidence check, and rule audit were applied on the same disagreement
set before synthesis. Round 3 narrows D-12 and D-21 substantially, but both still
fail on reserve-identity mechanics. D-23 remains open. D-24 now converges in a
strictly narrower form than the earlier Round 2 claims.

## X38-D-12: Clean OOS via future data

Your concession on layer ownership is correct. The FAIL-lineage record does **not**
belong in Topic 004's `knowledge/` transition store, and it does **not** require a
new Topic 002 `MetaLesson` category (`debate/004-meta-knowledge/final-resolution.md:227-244`;
`debate/002-contamination-firewall/final-resolution.md:139-149`;
`claude_code/round-3_author-reply.md:184-206`). The remaining dispute is narrower:
whether the proposed certification artifact is already sufficient.

It is not yet sufficient. F-12 makes two things true at once:
- a FAIL winner must survive as historical evidence/provenance, not anti-pattern
  (`debate/010-clean-oos-certification/findings-under-review.md:37-40`;
  `PLAN.md:546-555`;
  `x37/docs/gen1/RESEARCH_PROMPT_V7/PROMPT_FOR_V7_HANDOFF.md:53-60`
  [extra-archive]);
- the clean reserve is a one-shot append-only boundary, defined by executable
  timestamps (`debate/010-clean-oos-certification/findings-under-review.md:46-50,52-61`;
  `docs/design_brief.md:138-143`;
  `PLAN.md:531-539`).

Your `CertificationVerdict` sketch records the frozen spec and the pre-research
boundary, but it does not record the **actual append slice consumed by the
verdict**: no append-file identity, no end boundary, no immutable reserve-slice
reference (`claude_code/round-3_author-reply.md:215-225`). Without that, the
artifact cannot reconstruct which clean bars were burned. That matters immediately
for FAIL lineage, and it matters even more if Topic 010 later permits any
post-`INCONCLUSIVE` continuation. So I accept the certification-tier placement, but
I reject convergence on the current schema. X38-D-12 stays `Open`.

## X38-D-21: CLEAN_OOS_INCONCLUSIVE

I still reject the earlier `POWER_INFEASIBLE` direction and any fourth
certification verdict. Topic 007 and the Clean OOS prompt still support exactly
three certification outcomes, with honest `INCONCLUSIVE` when the reserve is
underpowered (`debate/007-philosophy-mission/final-resolution.md:64-79`;
`x37/docs/gen1/RESEARCH_PROMPT_V[n]/PROMPT_FOR_V[n]_CLEAN_OOS_V2[en].md:76-81`
[extra-archive]).

But your new repair closes only the **review-visibility** part of the gap. The
history fields are useful, yet they do not answer the more basic mechanism
question already inside F-21: it says `INCONCLUSIVE` means "wait for more data,
then re-run Clean OOS" (`debate/010-clean-oos-certification/findings-under-review.md:107-110`).
That collides with F-12's one-shot reserve law: the clean reserve opens exactly
once on genuinely appended data (`docs/design_brief.md:138-143`;
`PLAN.md:531-535`;
`x37/docs/gen1/RESEARCH_PROMPT_V[n]/PROMPT_FOR_V[n]_CLEAN_OOS_V2[en].md:27-30,72-81`
[extra-archive]).

Your Round 3 proposal adds `iteration_count` and `previous_verdicts`, but it still
does not define how attempt `N+1` remains a clean-OOS attempt after attempt `N`
has already opened the reserve (`claude_code/round-3_author-reply.md:278-326`).
Without an explicit rollover law such as "attempt `N+1` starts strictly after the
last clean bar consumed by attempt `N`," the proposal either reuses burned reserve
data or leaves the next clean window undefined. That is a mechanism dispute, not a
documentation gap. X38-D-21 stays `Open`.

## X38-D-23: Pre-existing candidates vs x38 winners

The negative boundary is now solid and I do not reopen it: same-dataset
pre-existing candidates stay shadow-only before freeze, they do not become default
certification inputs, and Clean OOS still certifies x38's frozen winner only
(`docs/design_brief.md:87-89`;
`PLAN.md:429-434,519-527`;
`x37/docs/gen1/RESEARCH_PROMPT_V[n]/PROMPT_FOR_V[n]_CLEAN_OOS_V2[en].md:70-75,90-96`
[extra-archive]).

The positive recording contract is still not closed. Topic 007 freezes a MUST-
surface rule only for **contradiction** with historical lineage
(`debate/007-philosophy-mission/final-resolution.md:90-95`). F-23 is broader: it
also needs handling for same-family rediscovery and `NO_ROBUST_IMPROVEMENT`
(`debate/010-clean-oos-certification/findings-under-review.md:145-153`). Your
Round 3 attempt overreads `drafts/architecture_spec.md:164-166` here. Topic 007
explicitly rejects encoding confirmation/divergence as formal sub-types within
coverage/process evidence because that polarity cross-cuts both same-archive
categories (`debate/007-philosophy-mission/final-resolution.md:94-102`). So the
proposed "convergence/divergence sub-type" is still in tension with the accepted
Decision 3 boundary (`claude_code/round-3_author-reply.md:78-100`).

The surviving open issue is therefore specific: Topic 010 still needs a below-
certification recording contract that covers the **full** F-23 scenario set
without importing certification-flow metadata and without reversing Topic 007's
rejected subtype move. X38-D-23 stays `Open`.

## X38-D-24: Clean OOS power rules

**Steel-man of my prior Open position**: convergence was premature because Topic
010 had not yet frozen the exact binding dimensions or derivation law. Calling the
issue settled while exposure hours, regime coverage, effect size, and method were
all still moving would only rename ambiguity, not resolve it
(`codex/round-2_reviewer-reply.md:143-159`;
`debate/010-clean-oos-certification/findings-under-review.md:191-235`).

That steel-man no longer holds. Round 3 withdraws the unsupported universal-gate
claims and narrows the design to what the sources actually back
(`claude_code/round-3_author-reply.md:124-169`). The Clean OOS prompt requires two
things up front: honest `INCONCLUSIVE` labeling when the reserve is underpowered,
and both a calendar-wait recommendation and a target trade-count recommendation
(`x37/docs/gen1/RESEARCH_PROMPT_V[n]/PROMPT_FOR_V[n]_CLEAN_OOS_V2[en].md:76-81,166-172`
[extra-archive]). F-24 itself then records the rest of the dimension set as open
proposal space, not frozen law
(`debate/010-clean-oos-certification/findings-under-review.md:191-235`).

So the converged v1 contract is method-first:
- before reserve evaluation, the campaign must declare the power method and the
  criteria that method will use;
- that declaration must, at minimum, include calendar-time and trade-count
  criteria;
- if the declared method says the reserve is underpowered, the verdict is
  `CLEAN_OOS_INCONCLUSIVE`;
- additional dimensions are method-dependent, not universal v1 gates.

Regime coverage does **not** survive as a frozen universal binding gate in this
topic. Topic 007 forbids external framework-provided regime classifiers, and no
policy-compatible binding classifier was established here
(`debate/007-philosophy-mission/final-resolution.md:112-116`). That leaves draft
work, not a live mechanism dispute. X38-D-24 is `Converged`.

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-D-12 | Certification-tier placement accepted; current FAIL-lineage artifact still underspecifies the consumed clean-reserve slice | Judgment call | Open | A certification-tier verdict artifact is enough to close FAIL-lineage recording because Topic 004 and Topic 002 are already ruled out | The proposed artifact omits actual append-slice identity/end-boundary, so it cannot reconstruct which clean bars were spent under the one-shot reserve law (`findings-under-review.md:46-61`; `docs/design_brief.md:138-143`; `claude_code/round-3_author-reply.md:215-225`) |
| X38-D-21 | Review-history fields help, but repeated-`INCONCLUSIVE` reruns still lack a clean-reserve rollover law | Thiếu sót | Open | `iteration_count` + `previous_verdicts` + existing `PENDING_CLEAN_OOS` review closes repeated-`INCONCLUSIVE` governance without a fourth verdict | It closes reviewer visibility, not evaluation validity; F-21 still says "wait more data, re-run Clean OOS" while F-12 keeps the reserve one-shot, and no rule defines how attempt `N+1` remains clean |
| X38-D-23 | Shadow-only boundary stands; full below-certification relation to pre-existing candidates still lacks a compliant carrier | Thiếu sót | Open | Topic 007 semantic rule + same-archive evidence already provide the full mechanism for surfacing the relation below certification | Topic 007 mandates explicit surfacing only for contradiction and separately rejects confirmation/divergence as formal same-archive sub-types; same-family rediscovery and `NO_ROBUST_IMPROVEMENT` remain uncovered (`debate/007-philosophy-mission/final-resolution.md:90-102`; `findings-under-review.md:145-153`) |
| X38-D-24 | Freeze method-first power law: predeclared campaign-specific method, honest `INCONCLUSIVE` when underpowered, calendar/trade-count criteria mandatory, extra dimensions method-dependent | Thiếu sót | Converged | Topic 010 could not converge until it froze one universal binding dimension set and exact derivation law directly | That objection fails once Topic 010 stops claiming a universal dimension set; the sources support a method-first contract with mandatory calendar/trade-count criteria and honest underpower labeling, not a stronger universal gate set (`PROMPT_FOR_V[n]_CLEAN_OOS_V2[en].md:76-81,166-172` [extra-archive]) |
