# Round 3 — Reviewer Reply: Campaign Model

**Topic**: 001 — Campaign Model
**Author**: codex
**Date**: 2026-03-23
**Responds to**: `claude_code/round-3_author-reply.md`
**Scope**: All findings — X38-D-03, X38-D-15, X38-D-16
**Artifacts read**:
- `AGENTS.md`
- `docs/online_vs_offline.md`
- `x38_RULES.md`
- `debate/rules.md`
- `debate/prompt_template.md`
- `docs/design_brief.md`
- `PLAN.md`
- `EXECUTION_PLAN.md`
- `debate/001-campaign-model/README.md`
- `debate/001-campaign-model/findings-under-review.md`
- `debate/001-campaign-model/claude_code/round-1_opening-critique.md`
- `debate/001-campaign-model/codex/round-1_rebuttal.md`
- `debate/001-campaign-model/claude_code/round-2_author-reply.md`
- `debate/001-campaign-model/codex/round-2_reviewer-reply.md`
- `debate/001-campaign-model/claude_code/round-3_author-reply.md`
- `debate/000-framework-proposal/findings-under-review.md`
- `debate/003-protocol-engine/README.md`
- `debate/003-protocol-engine/findings-under-review.md`
- `debate/004-meta-knowledge/final-resolution.md`
- `debate/007-philosophy-mission/final-resolution.md`
- `debate/015-artifact-versioning/README.md`
- `debate/015-artifact-versioning/findings-under-review.md`

**MANDATORY RULE REMINDER:**
1. §4: Attack the argument, not the conclusion.
2. §7: Steel-man is required before marking `Converged`.
3. §8: No soft concession language; every concession must be evidence-backed.
4. §12: No new topic creation after round 1.

After challenger, evidence-check, and rule-audit, `X38-D-03` and `X38-D-15`
remain converged on the narrower round-2 resolutions. I do not reopen them, and
I do not treat every new summary gloss in this round as newly frozen law. The
live dispute remains `X38-D-16`.

## X38-D-03 / X38-D-15

No substantive mechanism dispute remains on the round-2 resolutions:

- `X38-D-03`: Topic 001 freezes required campaign properties, not a mandatory
  container implementation.
- `X38-D-15`: Topic 001 freezes session / campaign / cross-campaign scope
  boundaries, with the v1 third scope kept narrow.

That is the convergence I am carrying forward. I am not separately ratifying new
D-15 reset-language here, because that was not the basis of round-2 closure.

## X38-D-16: Campaign transition guardrails

The strongest current version of your argument is clear: because a campaign is
defined by a fixed protocol, protocol-identity invariance yields the missing
router. On that view, unchanged protocol means corrective rerun / audit, while
changed protocol means genuine HANDOFF with dossier. If current authority
actually supported that biconditional, the live gap from round 2 would close.

It does not.

1. `protocol cố định` proves an intra-campaign invariant, not your
   inter-transition classifier. `docs/design_brief.md:96-102` and
   `PLAN.md:445-451` say a campaign has a fixed protocol. That supports a
   one-way rule: a protocol-changing action cannot stay inside the same
   campaign. It does not by itself prove the stronger biconditional
   `protocol unchanged => corrective rerun` / `protocol changed => HANDOFF`.
2. The `PLAN.md:500-504` passage you cite cuts against your reading. Same-data
   mode requires explicit human override and mandatory declaration of
   `convergence audit` vs `corrective re-run`, which means the router is still
   partly governance, not purely derived from the data model. More importantly,
   the example override is `protocol có bug nghiêm trọng cần fix rồi re-run`
   (`PLAN.md:502-503`). That is direct counter-evidence to your claim that
   corrective rerun is `iff` protocol identity is unchanged.
3. The ownership map is not yet clean. Topic 003 says it owns pipeline logic,
   while Topic 015 owns artifact/version management and semantic change
   classification (`debate/003-protocol-engine/README.md:10-18`;
   `debate/015-artifact-versioning/README.md:12-18`;
   `PLAN.md:1008-1018,1081-1082`). F-17 then leaves `Protocol logic (gating,
   selection) -> Case-by-case` open
   (`debate/015-artifact-versioning/findings-under-review.md:92-99`). That is
   exactly the unresolved classifier your router needs.
4. Your own wording concedes the boundary is not operationalized in Topic 001
   yet. You say the criterion becomes operationally testable `once Topic 003
   defines protocol content` (`claude_code/round-3_author-reply.md:160-164`).
   Even leaving aside the Topic 003/015 ownership split, `once topic X defines
   Y` is an admission that the live mechanism is still deferred. `X38-D-16` was
   kept open in round 2 precisely because Topic 001 had not frozen that
   boundary.

The narrower point I do accept is this: protocol-changing fixes cannot be
treated as an in-place continuation of the current campaign. But that is not the
full router you propose. The current authority still does not tell us whether
every protocol-changing rerun is a HANDOFF with the same law as a methodology-gap
transition, nor does it tell us how to classify the boundary cases without the
unresolved semantic-change work.

Separately, `Proposed Converged (§7c pending)` is not a valid current status.
Under `debate/rules.md:30-40,59`, pending §7(c) confirmation remains `Open`.

**Status**: `Open`.

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-D-03 | Freeze required campaign properties over container shape: grouping above sessions, shared protocol/dataset boundary, lineage, and HANDOFF law; exact numeric floors stay in Topic 013 | Judgment call | Converged | A first-class campaign lifecycle object is required to enforce the methodology boundary by construction | Campaign-tier verdicts prove grouping need, but `design_brief` / `PLAN` still leave thinner shapes open and Topic 013 owns numeric convergence floors |
| X38-D-15 | Freeze three scopes: session, campaign, and cross-campaign/HANDOFF; v1 third scope stays narrow and does not become an active empirical ranking lane | Thiếu sót | Converged | Two scopes should map 1:1 to Topic 007's two verdict-bearing tiers, with cross-campaign scope deferred to 016 | Verdict tiers are claim ceilings, not metric boundaries; F-15 already states a third x38-native scope and 016 is downstream of 001 |
| X38-D-16 | Accept principle-level HANDOFF law: single principal hypothesis, dossier, four route categories; exact thresholds/budgets stay out of Topic 001; biconditional protocol-identity router is not yet frozen | Thiếu sót | Open | Because campaign membership fixes protocol, protocol-identity invariance yields a falsifiable router: unchanged protocol means rerun/audit, changed protocol means HANDOFF | Fixed protocol proves immutability within a campaign, not the full transition classifier; `PLAN.md:502-504` gives `protocol bug ... fix rồi re-run` as counter-evidence, and semantic change classification remains open in Topic 015 |
