# Judgment-Call Memo — Topic 010 After Round 6

**Topic**: 010 — Clean OOS & Certification
**Role**: Codex (advisor for closure)
**Date**: 2026-03-25
**Decision owner**: human researcher (`debate/rules.md:78`)
**Mode**: advisory only; not Prompt C closure

Independent evidence review and citation audit are recommended before closure.
This memo reads all Topic 010 round files plus the cross-topic dependency surfaces
most likely to affect closure: Topic 003 (protocol engine), Topic 016 (bounded
recalibration), and Topic 017 (epistemic search policy / promotion ladder).

## 1. Per-Issue Summary

| Issue ID | Finding | Final positions | Agreement level | Recommended resolution |
|---|---|---|---|---|
| X38-D-12 | Clean OOS protocol | Claude Round 6: D-12 is no longer independently disputed; it tracks D-21 because F-12's short-data bullet is routed through F-21/F-24 (`findings-under-review.md:74-83`; `claude_code/round-6_author-reply.md:133-165`). Codex Round 6: accepts that dependency closeout and marks D-12 `Converged` once D-21's rerun rule is explicit (`codex/round-6_reviewer-reply.md:81-106`). | Converged | If you accept D-21's Round 6 explicit re-trigger clause as the adopted V1 contract, D-12 can be closed as `Converged`. Closure text should say explicitly that D-12 closes via D-21's adopted rerun governance, not via a separate new mechanism. |
| X38-D-21 | INCONCLUSIVE verdict state | Claude Round 6: repeated `INCONCLUSIVE` is governed by an explicit stateless re-trigger tied to the rolled-over boundary; no count-based `FAIL` (`claude_code/round-6_author-reply.md:45-114`). Codex Round 6: accepts that closeout, but only as a new explicit freeze; Codex does **not** accept the stronger claim that old canonical text had already frozen re-fire semantics (`codex/round-6_reviewer-reply.md:45-79`). | Converged | Recommended closure path: adopt the Round 6 explicit trigger clause in `final-resolution.md` and close as `Converged`. If you are unwilling to adopt that new explicit sentence, then D-21 falls back to a real judgment call about whether re-trigger semantics were already implicit or still missing. |
| X38-D-23 | Pre-existing candidates | Claude Round 6: Scenario 2 contradiction is settled; Scenario 1 depends on unresolved identity work; Scenario 3 is a derivable null state from shadow-only provenance + `NO_ROBUST_IMPROVEMENT` (`claude_code/round-6_author-reply.md:171-259`). Codex Round 6: accepts contradiction handling, shadow-only treatment, and x38-only certification, but keeps the issue `Open` because Scenario 1/3 may still need an explicit below-certification relation / lookup contract before closure (`codex/round-6_reviewer-reply.md:108-155`). | Disputed | Recommended resolution: `Judgment call`. Tradeoff only: Claude's side says Topic 010 is complete once contradiction surfacing, shadow-only provenance, and x38-only certification are frozen; Codex's side says closure should still freeze an explicit relation / lookup contract for Scenario 1 and Scenario 3. Do not pick a winner in the memo; this is the live human judgment. |
| X38-D-24 | Power rules | Claude Round 3 withdrew over-frozen gates and accepted method-first design (`claude_code/round-3_author-reply.md:124-170`). Codex Round 3 accepted the narrowed contract: predeclared campaign-specific method; mandatory calendar-time + trade-count criteria; honest `INCONCLUSIVE`; extra dimensions method-dependent (`codex/round-3_reviewer-reply.md:144-157`). Later rounds treat D-24 as closed (`claude_code/round-5_author-reply.md:191-194`; `codex/round-6_reviewer-reply.md:157-171`). | Converged | Close as `Converged`. No remaining mechanism dispute is visible in the round history. Closure work is ledger sync, not design arbitration. |

## 2. Steel-Man Audit

### Issues that completed §7(a)(b)(c)

- **X38-D-21**: complete.
  Claude Round 6 states Codex's strongest remaining objection explicitly: old
  sources froze the first trigger but not post-`INCONCLUSIVE` re-fire semantics
  (`claude_code/round-6_author-reply.md:45-57`). Claude then argues against that
  objection with the new explicit trigger clause (`claude_code/round-6_author-reply.md:59-98`).
  Codex Round 6 confirms that this *was* the strongest remaining objection and
  says the new explicit clause defeats it (`codex/round-6_reviewer-reply.md:47-79`).

- **X38-D-12**: complete, but derivative.
  Claude Round 6 explicitly accepts Codex's dependency objection: F-12 line 77
  routes through F-21/F-24, so D-12 tracks D-21 (`claude_code/round-6_author-reply.md:133-165`).
  Codex Round 6 then identifies that dependency as the strongest remaining
  objection and rejects it once D-21 is explicitly repaired
  (`codex/round-6_reviewer-reply.md:83-106`).
  This is a real §7 closeout, but it is derivative on D-21 rather than
  standalone.

- **X38-D-24**: complete.
  Claude Round 3 steel-mans the objection that exact binding dimensions were
  still unsettled (`claude_code/round-3_author-reply.md:111-123`) and narrows to
  method-first (`claude_code/round-3_author-reply.md:124-170`). Codex Round 3
  accepts that narrowed position and marks `Converged`
  (`codex/round-3_reviewer-reply.md:134-157`). Later rounds do not reopen it and
  instead treat it as already settled (`claude_code/round-5_author-reply.md:191-194`;
  `codex/round-6_reviewer-reply.md:157-171`).

### Issues with incomplete steel-man

- **X38-D-23**: incomplete.
  No round completes the full §7 chain for the issue as a whole. By Round 6 both
  sides agree on Scenario 2 contradiction, shadow-only provenance, and x38-only
  certification, but they still disagree on whether Scenario 1 / Scenario 3 need
  an explicit below-certification relation contract before closure
  (`claude_code/round-6_author-reply.md:230-259`;
  `codex/round-6_reviewer-reply.md:122-155`).

## 3. Cross-Topic Impact Check

### Topic 003 — protocol engine

- Topic 003's current finding is still the 8-stage discovery pipeline ending at
  Stage 8 internal evaluation (`debate/003-protocol-engine/findings-under-review.md:29-43`).
- Topic 010's settled direction is that Clean OOS sits **after** research as
  Phase 2, not inside those 8 stages (`docs/design_brief.md:120-145`;
  `PLAN.md:519-539`; `debate/010-clean-oos-certification/findings-under-review.md:244`).
- Advisory read: Topic 003 integrates cleanly only if it treats Clean OOS as a
  separate post-pipeline Phase 2 mechanism consuming the frozen winner and later
  certification artifacts, not as "Stage 9".

### Topic 016 — bounded recalibration

- Topic 016 explicitly says Topic 010 is a hard dependency, and its F-35 section
  treats Clean OOS interaction as unresolved if bounded recalibration is allowed
  (`PLAN.md:771-772`; `debate/016-bounded-recalibration-path/findings-under-review.md:121-191`).
- The critical conflict is unchanged: Topic 010's verdict states assume a frozen
  winner and a clean reserve opened exactly once, while Topic 016 asks whether a
  recalibrated candidate needs a new reserve, lightweight re-certification, or no
  re-certification (`debate/016-bounded-recalibration-path/findings-under-review.md:166-191,205`).
- Advisory read: Topic 010 does **not** yet account for recalibrated candidates.
  That is acceptable only because x38 still has no bounded recalibration path.
  If Topic 016 opens one, 016 must define the new certification interaction.

### Topic 017 — epistemic search policy

- ESP-03 already consumes Topic 010's power-floor logic directly: contradiction
  below power floor only triggers review; contradiction above power floor demotes
  the ladder (`debate/017-epistemic-search-policy/findings-under-review.md:214-221`).
- Topic 017 also states explicitly that promotion power floors should reuse Topic
  010 methodology (`debate/017-epistemic-search-policy/findings-under-review.md:257-258,354`).
- Advisory read: Topic 010's D-24 outcome is consistent with Topic 017 **if**
  Topic 017 reuses the method-first power methodology rather than assuming fixed
  numeric thresholds. Topic 017 should consume Topic 010's method contract, not
  invent a parallel power standard.

## 4. Status Drift Check

### Findings ledger vs latest round outcomes

| Surface | Current ledger | Latest round outcome | Flag |
|---|---|---|---|
| `findings-under-review.md` — X38-D-12 | `Open` (`findings-under-review.md:21-25`) | `Converged` in `codex/round-6_reviewer-reply.md:181-188` | `[WARNING]` |
| `findings-under-review.md` — X38-D-21 | `Open` (`findings-under-review.md:89-93`) | `Converged` in `codex/round-6_reviewer-reply.md:185-186` | `[WARNING]` |
| `findings-under-review.md` — X38-D-23 | `Open` (`findings-under-review.md:134-138`) | still `Open` in `codex/round-6_reviewer-reply.md:187` | `OK` |
| `findings-under-review.md` — X38-D-24 | `Open` (`findings-under-review.md:179-183`) | `Converged` since Round 3 and still `Converged` in `codex/round-6_reviewer-reply.md:188` | `[WARNING]` |

### Additional drift relevant to human closure

- `[NOTE]` Topic README status is still `OPEN` (`debate/010-clean-oos-certification/README.md:3-6`).
  That is still correct as long as D-23 remains unresolved for closure.

- `[NOTE]` Topic README cross-topic tensions omit the Topic 017 row that now
  appears in `findings-under-review.md` (`README.md:38-44` vs
  `findings-under-review.md:240-246`). That is not a status error, but it is a
  routing/completeness drift worth syncing before closure.

- `[WARNING]` If the human closure decides D-23 as a `Judgment call`, Topic 010's
  ledgers will need synchronized updates across `findings-under-review.md`,
  `README.md`, `PLAN.md`, and any closure artifact. Right now only the round
  history contains the D-23 tradeoff explicitly (`claude_code/round-6_author-reply.md:230-259`;
  `codex/round-6_reviewer-reply.md:145-179`).

## Advisory Bottom Line

- The round history supports treating **D-21** and **D-24** as true convergence.
- **D-12** is also closure-ready, but its convergence is derivative on adopting
  D-21's explicit Round 6 trigger clause.
- **D-23** is the only issue that still requires a human judgment call.
