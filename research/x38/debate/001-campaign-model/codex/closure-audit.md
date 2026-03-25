# Closure Audit — Topic 001: Campaign Model

**Auditor**: codex
**Date**: 2026-03-23
**Scope**: final-resolution.md + cross-file consistency
**Verdict**: PASS WITH NOTES

## A. Factual accuracy

- **D-03**: The closed resolution matches the round-2 record. The narrowed result in `debate/001-campaign-model/final-resolution.md:24`, `debate/001-campaign-model/final-resolution.md:32-44`, and `debate/001-campaign-model/final-resolution.md:201` aligns with `debate/001-campaign-model/claude_code/round-2_author-reply.md:46-94` and `debate/001-campaign-model/codex/round-2_reviewer-reply.md:37-59`.
- **D-03 note**: The rationale citation in `debate/001-campaign-model/final-resolution.md:42-44` is imprecise. `docs/design_brief.md:96-102` and `PLAN.md:445-451` define campaign contents, but the "thinner container shapes remain open" point is actually supported by `docs/design_brief.md:115-118`, `PLAN.md:491-494`, and Topic 013 ownership at `PLAN.md:974-975`.
- **D-15**: The closed resolution matches the round-2 record. Three scopes with a narrow v1 cross-campaign lane align with `debate/001-campaign-model/claude_code/round-2_author-reply.md:98-155` and `debate/001-campaign-model/codex/round-2_reviewer-reply.md:60-87`. The steel-man description in `debate/001-campaign-model/final-resolution.md:53-58` is faithful.
- **D-16**: Closure as a §14 Judgment call is accurate. The detailed restatements at `debate/001-campaign-model/final-resolution.md:72-82`, `debate/001-campaign-model/final-resolution.md:92-164`, and `debate/001-campaign-model/final-resolution.md:203` match the round-6 judgment setup in `debate/001-campaign-model/claude_code/round-6_author-reply.md:162-184` plus the still-open Codex position in `debate/001-campaign-model/codex/round-5_reviewer-reply.md:55-106`.
- **D-16 note**: The shorthand at `debate/001-campaign-model/final-resolution.md:63-65` compresses Position B to "wait for Topic 015 classifier." The fuller record was broader: Codex argued that the unresolved problem was the correctness boundary for `corrective_rerun` vs `genuine_HANDOFF`, with Topic 015/F-17 and Topic 003 both implicated (`debate/001-campaign-model/codex/round-4_reviewer-reply.md:73-98`, `debate/001-campaign-model/codex/round-5_reviewer-reply.md:59-89`). The later detailed wording fixes most of this, so this is a wording note, not an outcome-changing error.
- **F-16 four gaps**: The routing matrix alone does not cover all four stated gaps in `debate/001-campaign-model/findings-under-review.md:167-170`, but the full `§14 Judgment` package does. "When to open new campaign?" is handled by the routing matrix plus the one-way invariant (`debate/001-campaign-model/final-resolution.md:101-121`). "How much can change?" and "what evidence is required?" are handled by the HANDOFF package and dossier fields (`debate/001-campaign-model/final-resolution.md:105-108`, `debate/001-campaign-model/final-resolution.md:151-164`). "Cooldown" is handled indirectly via same-data governance and deferral of numeric ceilings to Topic 013 (`debate/001-campaign-model/final-resolution.md:102-104`, `debate/001-campaign-model/final-resolution.md:157`; `PLAN.md:500-506`).
- **Burden of proof / default HANDOFF**: `debate/001-campaign-model/final-resolution.md:110-120` is consistent with the authority set as a conservative judgment-call rule. It is not a direct quote from pre-closure authority, but it does fit the fixed-protocol axiom (`docs/design_brief.md:96-102`, `PLAN.md:445-451`) and the unresolved-proof posture captured in the round history.
- **`convergence_audit` annotation**: `debate/001-campaign-model/final-resolution.md:140-149` is consistent with `PLAN.md:504` only if read exactly as the file explains it, i.e. as a purpose-label axis separate from route/action. That is a defensible judgment-call interpretation, not a verbatim reading of pre-closure text.
- **Deferred owners**: The deferred items are correctly assigned. Topic 008/F-13 owns identity schema (`debate/008-architecture-identity/findings-under-review.md:120-140`), Topic 003/F-05 owns protocol content (`debate/003-protocol-engine/README.md:10-18`), Topic 013/F-31 owns thresholds and same-data ceilings (`debate/013-convergence-analysis/findings-under-review.md:81-139`), Topic 015/F-17 owns evidence classes and invalidation scope (`debate/015-artifact-versioning/findings-under-review.md:90-99`), and Topic 016 owns recalibration exceptions (`debate/016-bounded-recalibration-path/findings-under-review.md:22-107`).

## B. Template D compliance

- Decisions table present and complete.
- Key design decisions section present.
- Unresolved tradeoffs section present.
- Draft impact table present.
- Header fields present: Topic ID, Opened, Closed, Rounds, Participants.
- Extra sections (`Summary`, `§14 Judgment`, `Agreed Elements`, `Cross-topic tensions`, `Complete Status Table`) are additive and do not conflict with Template D.

## C. Internal consistency

- Decision summaries, key design decisions, `§14 Judgment`, agreed elements, and the complete status table are materially aligned on D-03 and D-15.
- D-16 is consistently marked as a Judgment call, not a convergence.
- D-16 status vocabulary is not internally clean across the closure package. The rules and Prompt C use `Judgment call` as the canonical post-§14 status (`debate/rules.md:68-70`, `debate/prompt_template.md:137-143`), but Topic 001 also uses `Decided` in several places. That does not change the outcome, but it is status-schema drift.
- Two cleanup issues remain inside `debate/001-campaign-model/final-resolution.md`:
- Route label naming drifts between `corrective_re_run` (`:111`, `:118`, `:138`) and `corrective_rerun` (`:175`).
- The D-16 short description at `:63-65` is narrower than the fuller restatements later in the file.

## D. Cross-file consistency

- `debate/001-campaign-model/findings-under-review.md`: statuses consistent. D-03 = Converged (`:22`), D-15 = Converged (`:88`), D-16 = Decided / §14 Judgment call (`:135`). Summary table agrees (`:214-216`).
- `debate/001-campaign-model/README.md`: CLOSED and 3/3 resolved are consistent (`:5`, `:29-31`).
- `debate/debate-index.md`: CLOSED row and totals are consistent (`:5`, `:16`, `:33`).
- `PLAN.md`: the closure note and topic table are consistent (`:512-517`, `:737`), and the debate execution summary is also consistent (`:1064`).
- `PLAN.md` note: the later live-status block is stale. `PLAN.md:1076-1081` still omits Topic 001 from `Topics CLOSED` and still lists it inside Wave 2 open work, which conflicts with the closed-topic lines above.
- `EXECUTION_PLAN.md`: current-status row, wave table, and closure sync note are consistent (`:27`, `:193`, `:204-209`).
- `docs/evidence_coverage.md`: Topic 001 header and closure sync notes are consistent (`:355`, `:363-388`).
- Status-schema drift note: Topic 001 mixes `Judgment call` and `Decided` for D-16 across the closure package. The canonical rules language is `Judgment call`, but `Decided` appears in `debate/001-campaign-model/findings-under-review.md:135`, `debate/001-campaign-model/findings-under-review.md:216`, `debate/001-campaign-model/README.md:30`, `debate/debate-index.md:16`, and `debate/001-campaign-model/final-resolution.md:15`, `debate/001-campaign-model/final-resolution.md:203`.
- Cross-file drift note: D-15 classification remains `Judgment call` in `debate/001-campaign-model/findings-under-review.md:85` and `debate/001-campaign-model/findings-under-review.md:215`, while the round-2+ closure record and `debate/001-campaign-model/final-resolution.md:202` treat it as `Thiếu sót`.

## E. Cross-topic tensions

- All 8 entries are materially grounded, and the new 008/F-13 entry is properly supported by `debate/008-architecture-identity/findings-under-review.md:120-140`.
- Downstream ownership assignments are correct for 008, 003, 013, 015, and 016.
- One rules-format issue remains across `debate/001-campaign-model/findings-under-review.md:201`, `debate/001-campaign-model/README.md:39`, and `debate/001-campaign-model/final-resolution.md:188`: the Topic 003 row uses `—` instead of a specific finding, but `debate/rules.md:158-160` requires a concrete finding reference. This should name `F-05`.

## F. Position C assessment (advisory)

- Advisory only: Position C is internally coherent. It preserves Position A's structural law, preserves Position B's concern that ambiguous cases cannot be waved away as already-classified, and makes the route/action vs purpose-label split explicit.
- Advisory only: the two-axis split is sound, but future spec text should define `convergence_audit` carefully so readers do not collapse it back into the older "same-protocol audit only" meaning.
- Advisory only: default-to-HANDOFF is conservative and governance-safe. It reads as a judgment-layer choice rather than a direct quote from earlier authority, which is acceptable under `debate/rules.md:68-70` as long as it stays clearly marked as the human decision.

## Issues found

| # | Severity | File | Issue |
|---|----------|------|-------|
| 1 | Medium | `debate/001-campaign-model/final-resolution.md` | D-03 rationale at `:42-44` cites the wrong supporting lines for "thinner container shapes remain open" and Topic 013 ownership. |
| 2 | Medium | `debate/001-campaign-model/findings-under-review.md`, `debate/001-campaign-model/final-resolution.md`, `debate/001-campaign-model/README.md`, `debate/debate-index.md` | D-16 mixes non-canonical `Decided` with canonical `Judgment call`. `debate/rules.md:68-70` and `debate/prompt_template.md:137-143` require `Judgment call` after max rounds. |
| 3 | Medium | `PLAN.md` | Topic 001 is closed in `PLAN.md:512-517`, `PLAN.md:737`, and `PLAN.md:1064`, but still appears in open-work lines `PLAN.md:1076-1081`. |
| 4 | Low | `debate/001-campaign-model/findings-under-review.md` | D-15 classification drifts across closure artifacts: `:85` and `:215` still say `Judgment call`, while the round-2+ closure record and `debate/001-campaign-model/final-resolution.md:202` use `Thiếu sót`. |
| 5 | Low | `debate/001-campaign-model/final-resolution.md` | Route label spelling is inconsistent: `corrective_re_run` at `:111`, `:118`, `:138` vs `corrective_rerun` at `:175`. |
| 6 | Low | `debate/001-campaign-model/findings-under-review.md`, `debate/001-campaign-model/README.md`, `debate/001-campaign-model/final-resolution.md` | Topic 003 tension row omits the required specific finding (`F-05`), using `—` at `:201`, `:39`, and `:188` contrary to `debate/rules.md:158-160`. |

## Recommendation

ACCEPT with corrections. No issue found changes the closure outcome or justifies reopening Topic 001. Fix the D-03 citation drift, normalize D-16 status language to `Judgment call`, sync the stale `PLAN.md` live-status block, then clean up the D-15 classification drift, route-label spelling, and Topic 003 finding reference so the closure package is fully self-consistent.
