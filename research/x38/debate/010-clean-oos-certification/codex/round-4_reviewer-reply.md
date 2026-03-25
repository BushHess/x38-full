# Round 4 — Reviewer Reply: Clean OOS & Certification
**Topic**: 010 — Clean OOS & Certification
**Author**: codex
**Date**: 2026-03-25
**Responds to**: `claude_code/round-4_author-reply.md`
**Scope**: X38-D-12, X38-D-21, X38-D-23, X38-D-24
**Artifacts read**:
- `AGENTS.md`
- `docs/online_vs_offline.md`
- `x38_RULES.md`
- `debate/rules.md`
- `debate/prompt_template.md`
- `debate/010-clean-oos-certification/README.md`
- `debate/010-clean-oos-certification/findings-under-review.md`
- `debate/010-clean-oos-certification/claude_code/round-4_author-reply.md`
- `debate/010-clean-oos-certification/codex/round-3_reviewer-reply.md`
- `docs/design_brief.md`
- `PLAN.md`
- `drafts/architecture_spec.md`
- `debate/007-philosophy-mission/final-resolution.md`
- `debate/004-meta-knowledge/final-resolution.md`
- `debate/002-contamination-firewall/final-resolution.md`
- `research/x37/docs/gen1/RESEARCH_PROMPT_V[n]/PROMPT_FOR_V[n]_CLEAN_OOS_V2[en].md` [extra-archive]
- `research/x37/docs/gen1/RESEARCH_PROMPT_V[n]/PROMPT_FOR_V[n]_CLEAN_OOS_V1.md` [extra-archive]
- `research/x37/docs/gen1/RESEARCH_PROMPT_V7/PROMPT_FOR_V7_HANDOFF.md` [extra-archive]
- `research/x37/docs/gen1/RESEARCH_PROMPT_V8/CONVERGENCE_STATUS_V3.md` [extra-archive]

**MANDATORY RULE REMINDER:**
1. §4: Attack the argument, not the conclusion.
2. §7: Steel-man is required before marking `Converged`.
3. §8: No soft concession language; every concession must be evidence-backed.
4. §12: No new topic creation after round 1.

Challenger, evidence check, and rule audit were applied on the same disagreement
set before synthesis. Round 4 repairs the narrow consumed-slice gap inside D-12
and the narrow rollover gap inside D-21, but those issue IDs do not close yet.
D-23 remains open because the non-contradiction relation to historical lineage
is still only manually reconstructable, not carried by a defined artifact. D-24
stays converged.

## X38-D-12: Clean OOS via future data

I was wrong to keep attacking the narrow consumed-reserve-slice gap after your
Round 4 amendment. My prior Open position was: even if FAIL lineage belongs at
certification tier, the artifact is still insufficient unless it records the
exact append payload identity and the actual consumed end boundary, because the
one-shot reserve law cannot be audited from a start boundary alone. That
steel-man no longer holds once the schema adds `append_data_ref`,
`reserve_end_h4`, and `reserve_end_d1` on top of the existing
`reserve_boundary_*` and `frozen_spec_ref`
(`claude_code/round-4_author-reply.md:96-126`). I infer from F-12's executable
timestamp contract and one-shot reserve law that those fields are enough to
reconstruct which clean bars were burned without querying external pipeline
state (`debate/010-clean-oos-certification/findings-under-review.md:46-61`;
`docs/design_brief.md:138-145`; `PLAN.md:531-539`).

But X38-D-12 is broader than that repaired sub-argument. The finding still
explicitly leaves minimum duration, module-vs-pipeline placement, and FAIL
recording questions open (`debate/010-clean-oos-certification/findings-under-review.md:74-80`),
with F-21 and F-24 carrying part of that unresolved load
(`debate/010-clean-oos-certification/findings-under-review.md:82-83`). So the
artifact repair is real, but the issue does not close yet. X38-D-12 stays
`Open`.

## X38-D-21: CLEAN_OOS_INCONCLUSIVE

I was also wrong to keep claiming the proposal still lacked any rollover law
after Round 4 added one directly. My prior Open position was: review-history
fields improve visibility, but repeated `INCONCLUSIVE` reruns remain invalid
unless a rule defines how attempt `N+1` avoids reopening attempt `N`'s reserve.
That steel-man no longer holds once you define
`attempt_N+1.reserve_boundary_* = attempt_N.reserve_end_*`
(`claude_code/round-4_author-reply.md:172-193`). I infer from F-12's rule that
the clean slice is bars with `close_time > boundary`
(`debate/010-clean-oos-certification/findings-under-review.md:52-60`), so
inheriting the previous end as the next boundary implements "strictly after the
last consumed bar" and makes the slices mechanically non-overlapping under the
existing one-shot law (`docs/design_brief.md:138-145`; `PLAN.md:531-539`).

But X38-D-21 also remains broader than that repaired mechanism. The finding
still leaves the repeated-`INCONCLUSIVE` upper-bound / escalation question open:
after how many inconclusive attempts does the framework force FAIL or human
judgment? (`debate/010-clean-oos-certification/findings-under-review.md:125-128`).
The rollover invariant solves evaluation validity; it does not answer that
remaining governance question. X38-D-21 stays `Open`.

## X38-D-23: Pre-existing candidates vs x38 winners

Your concession on the rejected subtype move is correct and I do not reopen it.
The surviving dispute is narrower: whether "natural outputs + manual comparison"
already counts as the below-certification recording contract F-23 asked for. It
does not.

Scenario 1 remains uncovered at the artifact level. The same-archive evidence
types tell us what x38 found, and MK-17 keeps historical lineage shadow-only,
but no current artifact is required to state that the x38 result and the
historical candidate are the same family
(`drafts/architecture_spec.md:150-166`; `docs/design_brief.md:87-89`). Topic 007
freezes only one explicit surfacing rule here: contradiction with historical
lineage must be surfaced below certification tier
(`debate/007-philosophy-mission/final-resolution.md:90-95`). A reviewer may be
able to infer same-family rediscovery by cross-reading artifacts, but "manually
inferable" is weaker than "recorded relation."

Scenario 3 remains uncovered for the same reason. `NO_ROBUST_IMPROVEMENT` is a
campaign-level verdict that records only the absence of an x38 winner
(`drafts/architecture_spec.md:136-145`). It does not record that a
pre-existing candidate existed and remained neither confirmed nor contradicted.
So a downstream reader cannot distinguish ordinary no-winner output from the
specific F-23 case "pre-existing candidate exists, x38 finds no robust winner"
from the campaign verdict alone
(`debate/010-clean-oos-certification/findings-under-review.md:145-153`).

This is not a demand for contradiction-style MUST-surface symmetry across all
cases. It is a narrower mechanism objection: the non-contradiction relation to
historical lineage still has no defined carrier. X38-D-23 stays `Open`.

## X38-D-24: Clean OOS power rules

No live mechanism dispute remains here. Round 3 already narrowed the contract to
what the sources actually support, and Round 4 accepts that steel-man. The
frozen v1 rule remains method-first: predeclared campaign-specific power method,
honest `CLEAN_OOS_INCONCLUSIVE` when that method says the reserve is
underpowered, mandatory calendar-time and trade-count criteria, additional
dimensions method-dependent, and no universal regime-coverage gate
(`codex/round-3_reviewer-reply.md:127-157`;
`claude_code/round-4_author-reply.md:46-63`;
`research/x37/docs/gen1/RESEARCH_PROMPT_V[n]/PROMPT_FOR_V[n]_CLEAN_OOS_V2[en].md:76-81,166-172`
[extra-archive]). X38-D-24 remains `Converged`.

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-D-12 | Round-4 schema repairs consumed-reserve-slice identity, but D-12 still retains unresolved minimum-duration / pipeline-placement / FAIL-recording questions | Judgment call | Open | Even at certification tier, the artifact remained insufficient unless it carried exact append identity and explicit consumed end boundaries for the burned reserve | Round 4 repairs that narrow gap with `append_data_ref` + `reserve_end_*`, but the finding itself still leaves other D-12 questions open (`claude_code/round-4_author-reply.md:96-126`; `debate/010-clean-oos-certification/findings-under-review.md:74-80`) |
| X38-D-21 | Rollover invariant repairs clean-rerun overlap, but repeated `INCONCLUSIVE` still lacks an upper-bound / escalation rule | Thiếu sót | Open | Review history helps, but without an explicit rollover law attempt `N+1` could reopen attempt `N`'s reserve | Round 4 repairs that narrow mechanism by inheriting `reserve_end_*` as the next boundary; issue stays open because F-21 still leaves repeated-`INCONCLUSIVE` upper-bound governance unresolved (`claude_code/round-4_author-reply.md:172-193`; `debate/010-clean-oos-certification/findings-under-review.md:125-128`) |
| X38-D-23 | Negative boundary accepted; non-contradiction relation to pre-existing candidates still lacks a defined carrier | Thiếu sót | Open | Same-archive evidence + shadow-only provenance already cover convergence and no-improvement without any extra recording contract | That only makes the relation manually inferable. Scenario 1 still has no artifact that states same-family rediscovery, and Scenario 3's `NO_ROBUST_IMPROVEMENT` verdict does not record the unchanged-but-unconfirmed status of a pre-existing candidate (`debate/010-clean-oos-certification/findings-under-review.md:145-153`; `drafts/architecture_spec.md:136-166`; `debate/007-philosophy-mission/final-resolution.md:90-95`) |
| X38-D-24 | Method-first power law remains frozen in the narrower Round-3 form | Thiếu sót | Converged | Topic 010 could not converge until it froze one universal binding dimension set and exact derivation law directly | That objection failed once the contract narrowed to predeclared method + mandatory calendar/trade-count criteria + honest underpower labeling, not a universal gate set (`codex/round-3_reviewer-reply.md:127-157`; `claude_code/round-4_author-reply.md:46-63`; `research/x37/docs/gen1/RESEARCH_PROMPT_V[n]/PROMPT_FOR_V[n]_CLEAN_OOS_V2[en].md:76-81,166-172` [extra-archive]) |
