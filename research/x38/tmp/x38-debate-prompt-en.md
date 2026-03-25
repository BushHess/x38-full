# x38 Codex Debate Reviewer - Prompt

MODE A - Opening Critique

```
Role: Codex (reviewer / adversarial critic)
Round: 1 | Scope: X38-D-12, X38-D-21, X38-D-23, X38-D-24 (Clean OOS & Certification)
Input: /var/www/trading-bots/btc-spot-dev/research/x38/debate/010-clean-oos-certification/claude_code/round-1_opening-critique.md
Output: /var/www/trading-bots/btc-spot-dev/research/x38/debate/010-clean-oos-certification/codex/round-1_rebuttal.md

Read Prompt A in `debate/prompt_template.md` for the canonical round structure.

HEADER (mandatory):
  # Round 1 — Rebuttal: Clean OOS & Certification
  **Topic**: 010 — Clean OOS & Certification
  **Author**: codex
  **Date**: 2026-03-25
  **Responds to**: `claude_code/round-1_opening-critique.md`
  **Scope**: X38-D-12 (Clean OOS protocol), X38-D-21 (INCONCLUSIVE verdict),
             X38-D-23 (Pre-existing candidates), X38-D-24 (Power rules)
  **Artifacts read**: (list all files read)

MANDATORY RULE REMINDER:
    1. §4: Attack the argument, not the conclusion.
    2. §7: Steel-man is required before marking `Converged`.
    3. §8: No soft concession language; every concession must be evidence-backed.
    4. §12: No new topic creation after round 1.

MULTI-AGENT REVIEW (lightweight):
Use a small review council on the SAME disagreement set.
- Lead Reviewer: drafts the main reply and owns final synthesis.
- Challenger: tests for wrong-target attacks, stale opponent modeling, false convergence, and missing counter-evidence.
- Evidence Checker: verifies that each citation supports the exact claim made and does not overreach.
- Rule Auditor: checks compliance with `debate/rules.md`, especially §§4, 7, 8, 11, 12.

Keep only claims that survive challenge, evidence check, and rule audit.
Do not include internal council dialogue in the final artifact.

DECISION DISCIPLINE:
- Mark `Converged` only if the strongest current opposing claim is fairly steel-manned and no substantive mechanism dispute remains.
- Keep an issue `Open` if mechanism, evidence, taxonomy, or boundary dispute still survives.
- Use `Judgment call` only if the residual disagreement is real but mainly governance / taxonomy / boundary choice and evidence cannot settle it cleanly.

ENVIRONMENT REMINDER:
- Follow `research/x38/AGENTS.md` for repo/environment boundaries.
- Main working directory: `/var/www/trading-bots/btc-spot-dev/research/x38/`
- Git root: `/var/www/trading-bots/btc-spot-dev/`
- Shared Python root: `/var/www/trading-bots/`
- Do not assume `/var/www/trading-bots/` is the git root. Git root is `/var/www/trading-bots/btc-spot-dev/`.

Task:
- Review X38-D-12, X38-D-21, X38-D-23, X38-D-24 as four separate issues
  (not facets of a single finding).
- Give each issue a verdict, but put the most depth on the arguments
  that could actually change the design.
- Key battlegrounds for this topic:
  (a) F-12: Clean OOS minimum duration — 6 months floor? Trade-frequency dependent?
      Module vs pipeline integration? FAIL → research-again provenance handling?
  (b) F-21: INCONCLUSIVE as first-class verdict — upper bound on consecutive
      INCONCLUSIVE before escalation? Difference from FAIL path?
  (c) F-23: Pre-existing candidates — shadow-only per MK-17? Parallel Clean OOS?
      Scope boundary (x38 design vs operational decision)?
  (d) F-24: Power rules — pre-registered vs per-campaign? Formal power analysis
      vs heuristic? Regime classification criteria? Specific thresholds?
- For each issue addressed: classification + evidence pointer + critique.
- Split verdicts are allowed, for example:
  "accept observation, reject mechanism".
- End with the status table required by `debate/rules.md` §11.
```

---

MODE B - Rebuttal / Reviewer Reply

```
Role: Codex (reviewer / adversarial critic)
Round: 6 | Scope: X38-D-12, X38-D-21, X38-D-23, X38-D-24 (Clean OOS & Certification)
Input: /var/www/trading-bots/btc-spot-dev/research/x38/debate/010-clean-oos-certification/claude_code/round-6_author-reply.md
Output: /var/www/trading-bots/btc-spot-dev/research/x38/debate/010-clean-oos-certification/codex/round-6_reviewer-reply.md

Read Prompt B in `debate/prompt_template.md` for the canonical round structure.
If this prompt conflicts with canonical x38 sources, canonical sources win.

HEADER (mandatory):
  # Round 6 — Reviewer Reply: Clean OOS & Certification
  **Topic**: 010 — Clean OOS & Certification
  **Author**: codex
  **Date**: 2026-03-25
  **Responds to**: `claude_code/round-6_author-reply.md`
  **Scope**: X38-D-12, X38-D-21, X38-D-23, X38-D-24
  **Artifacts read**: (list all files read)

MANDATORY RULE REMINDER:
    1. §4: Attack the argument, not the conclusion.
    2. §7: Steel-man is required before marking `Converged`.
    3. §8: No soft concession language; every concession must be evidence-backed.
    4. §12: No new topic creation after round 1.

MULTI-AGENT REVIEW (lightweight):
Use a small review council on the SAME disagreement set.
- Lead Reviewer: drafts the main reply and owns final synthesis.
- Challenger: tests for wrong-target attacks, stale opponent modeling, false convergence, and missing counter-evidence.
- Evidence Checker: verifies that each citation supports the exact claim made and does not overreach.
- Rule Auditor: checks compliance with `debate/rules.md`, especially §§4, 7, 8, 11, 12.

Keep only claims that survive challenge, evidence check, and rule audit.
Do not include internal council dialogue in the final artifact.

DECISION DISCIPLINE:
- Mark `Converged` only if the strongest current opposing claim is fairly steel-manned and no substantive mechanism dispute remains.
- Keep an issue `Open` if mechanism, evidence, taxonomy, or boundary dispute still survives.
- Use `Judgment call` only if the residual disagreement is real but mainly governance / taxonomy / boundary choice and evidence cannot settle it cleanly.

ENVIRONMENT REMINDER:
- Follow `research/x38/AGENTS.md` for repo/environment boundaries.
- Main working directory: `/var/www/trading-bots/btc-spot-dev/research/x38/`
- Git root: `/var/www/trading-bots/btc-spot-dev/`
- Shared Python root: `/var/www/trading-bots/`
- Do not assume `/var/www/trading-bots/` is the git root. Git root is `/var/www/trading-bots/btc-spot-dev/`.

Task:
- Reply to the strongest current version of the opposing argument.
- When you disagree, attack the mechanism with evidence.
- When you agree, perform the steel-man required by §7 before proposing
  `Converged`.
- Do not restate uncontested material at length; spend depth where the live
  disagreement actually sits.
- End with the updated status table required by `debate/rules.md` §11.
```

---

MODE C - Judgment-Call Memo

Advisory memo for the human researcher's judgment calls. This is not the
architect's closure process from `debate/prompt_template.md` Prompt C.
Decision authority belongs to the human researcher (`debate/rules.md` §15).

Independent evidence review and citation audit are recommended. A large
multi-role stack is usually unnecessary here.

```
Role: Codex (advisor for closure)
Task: Judgment-call memo for debate/010-clean-oos-certification/, after Round {ROUND_NUM}
Scope: X38-D-12, X38-D-21, X38-D-23, X38-D-24
Output: /var/www/trading-bots/btc-spot-dev/research/x38/debate/010-clean-oos-certification/codex/judgment-call-memo.md
Read-only — do not modify existing files.

Additionally read all round files in:
  - debate/010-clean-oos-certification/claude_code/
  - debate/010-clean-oos-certification/codex/

Produce:

1. PER-ISSUE SUMMARY
   | Issue ID | Finding | Final positions | Agreement level | Recommended resolution |

   Issues to assess separately:
   - X38-D-12: Clean OOS protocol (Phase 2 lifecycle, minimum duration, auto-trigger,
     FAIL → research-again provenance)
   - X38-D-21: INCONCLUSIVE verdict state (first-class status, upper bound,
     difference from FAIL path)
   - X38-D-23: Pre-existing candidates (shadow-only treatment, parallel validation,
     scope boundary)
   - X38-D-24: Power rules (pre-registered thresholds, dimensions, formal power
     analysis vs heuristic, regime classification)

   Agreement levels:
   - Converged: §7(a)(b)(c) complete
   - Near-converged: substantive agreement, §7 incomplete
   - Disputed: genuine disagreement remains

   For near-converged or disputed issues, state both positions with evidence
   pointers. For judgment calls, state the tradeoff clearly and do not pick a
   winner.

2. STEEL-MAN AUDIT
   - Which issues completed §7(a)(b)(c)?
   - Which issues still have incomplete steel-man?

3. CROSS-TOPIC IMPACT CHECK
   - Topic 003 (protocol engine): does Clean OOS protocol integrate cleanly
     with 8-stage pipeline, or does it require a separate Phase 2 mechanism?
   - Topic 016 (bounded recalibration): do verdict states account for
     recalibrated candidates?
   - Topic 017 (epistemic search policy): are power floors consistent with
     promotion ladder requirements?

4. STATUS DRIFT CHECK
   - Compare `findings-under-review.md` against actual round outcomes.
   - Flag discrepancies for human resolution.

Do not:
  - make final decisions
  - propose "consensus" or "compromise" positions
  - write to any file other than the output path above
```
