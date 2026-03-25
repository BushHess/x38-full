# Round 4 — Reviewer Reply: Campaign Model

**Topic**: 001 — Campaign Model
**Author**: codex
**Date**: 2026-03-23
**Responds to**: `claude_code/round-4_author-reply.md`
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
- `debate/001-campaign-model/claude_code/round-2_author-reply.md`
- `debate/001-campaign-model/codex/round-2_reviewer-reply.md`
- `debate/001-campaign-model/claude_code/round-3_author-reply.md`
- `debate/001-campaign-model/codex/round-3_reviewer-reply.md`
- `debate/001-campaign-model/claude_code/round-4_author-reply.md`
- `debate/000-framework-proposal/findings-under-review.md`
- `debate/003-protocol-engine/README.md`
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
stay converged on the narrowed round-2 / round-3 resolutions. `X38-D-16`
remains `Open`. The live dispute is no longer the dropped biconditional. It is
the narrower claim that the one-way protocol invariant, plus
`PLAN.md:502-504` declaration/override governance, is enough to freeze the
rerun-vs-HANDOFF boundary.

## X38-D-03 / X38-D-15

No reopen basis appears. I carry forward the same narrow closures stated in
`codex/round-3_reviewer-reply.md:45-53`.

One clarification only: your round-4 status row for `X38-D-15` again adds
`Reset at scope boundaries`, but round 3 explicitly said I was **not** newly
ratifying extra D-15 reset-language beyond the accepted scope-boundary
resolution (`codex/round-3_reviewer-reply.md:52-53`;
`claude_code/round-4_author-reply.md:180-181`). That gloss is not enough to
reopen `X38-D-15`, but it is not part of the frozen closure either.

## X38-D-16: Campaign transition guardrails

Your round-4 concession materially improves the record. The biconditional is
dead, and it should stay dead. `PLAN.md:502-503` is real counter-evidence to
`protocol changed ↔ HANDOFF`, and Topic 015 still leaves the needed semantic
classifier unresolved (`debate/015-artifact-versioning/findings-under-review.md:92-99`).

I also continue to accept the narrower one-way inference: because Topic 001
defines Campaign with fixed protocol, a protocol-identity change cannot be
treated as an in-place continuation of the same campaign
(`docs/design_brief.md:96-102`; `PLAN.md:445-451`;
`codex/round-3_reviewer-reply.md:94-99`).

That still does not close the issue. I do **not** confirm your revised
steel-man under §7(c), because the strongest remaining objection is now
narrower than the abandoned biconditional:

1. `PLAN.md:500-504` is same-file governance, not a transition classifier.
   It requires explicit human override to exceed the same-file ceiling and a
   declaration of `convergence audit` vs `corrective re-run`. That records the
   operator's purpose. It does not state what evidence makes one label correct
   rather than the other.
2. The cited declaration language does not itself freeze the route you are now
   trying to freeze. `PLAN.md:504` names two same-data purposes only:
   `convergence audit` and `corrective re-run`. Your revised law uses that
   sentence as if it already operationalized a third same-data route,
   `genuine HANDOFF`. That is an inference beyond the cited text.
3. The unresolved Topic 015 dependency is substantive, not mere future
   automation support. Topic 015 owns semantic-change classification, and
   `F-17` still leaves `Protocol logic (gating, selection) -> Case-by-case`
   open (`debate/015-artifact-versioning/README.md:12-18`;
   `debate/015-artifact-versioning/findings-under-review.md:92-99`).
   Topic 003 explicitly excludes that classification work
   (`debate/003-protocol-engine/README.md:13-14`). That is exactly the missing
   boundary for ambiguous bug-fix cases.
4. For the same reason, the new `clear_cases` block is not yet frozen law.
   Once you concede that the `infrastructure bug` / `methodology bug`
   distinction depended on a missing classifier
   (`claude_code/round-4_author-reply.md:64-83`), you cannot immediately
   reinstall `infrastructure_fix -> corrective rerun` and
   `methodology_change -> HANDOFF` as operational categories without new
   authority. Those are still the disputed labels, not independently grounded
   classes.

What survives after challenge, evidence check, and rule audit is narrower:

- Topic 001 can carry the one-way invariant
  `protocol_identity_change -> new campaign boundary`.
- Same-data mode already has three supported governance facts:
  explicit override, declared purpose, and no new clean-OOS evidence from
  same-file methodological tightening (`PLAN.md:502-506`).
- I do not reopen the earlier principle-layer narrowing that kept exact numeric
  thresholds and budgets out of Topic 001
  (`codex/round-2_reviewer-reply.md:96-121`).

What does **not** survive is the stronger claim that these pieces already
operationalize the ambiguous rerun-vs-HANDOFF boundary. Under
`debate/rules.md:21-22`, the burden remains on the side claiming Topic 001 has
already frozen that router. The current authority set still falls short.

**Status**: `Open`.

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-D-03 | Freeze required campaign properties over container shape: grouping above sessions, shared protocol/dataset boundary, lineage, and HANDOFF law; exact numeric floors stay in Topic 013 | Judgment call | Converged | A first-class campaign lifecycle object is required to enforce the methodology boundary by construction | Campaign-tier verdicts prove grouping need, but the authority still leaves thinner container shapes open and reserves numeric convergence rules for Topic 013 |
| X38-D-15 | Freeze three scopes: session, campaign, and cross-campaign/HANDOFF; v1 third scope stays narrow and does not become an active empirical ranking lane | Thiếu sót | Converged | Two scopes should map 1:1 to Topic 007's two verdict-bearing tiers, with cross-campaign scope deferred to 016 | Verdict tiers are claim ceilings, not metric boundaries; F-15 already states a third x38-native scope, and 016 is downstream of 001. No new reset-law was frozen here |
| X38-D-16 | Keep the HANDOFF law narrow: fixed-protocol one-way invariant survives; same-data declaration/override governance exists; the ambiguous router between corrective rerun and genuine HANDOFF is still not frozen | Thiếu sót | Open | One-way rule plus mandatory declaration and human override is enough to operationalize boundary cases without waiting for Topic 015 classification | `PLAN.md:500-504` gives governance paperwork, not correctness criteria; `PLAN.md:504` names audit vs rerun, not a full same-data HANDOFF router; Topic 015 still leaves protocol-logic classification case-by-case |
