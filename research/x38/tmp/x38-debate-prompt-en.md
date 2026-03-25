# x38 Codex Debate Reviewer - Prompt

MODE A - Opening Critique

```
Role: Codex (reviewer / adversarial critic)
Round: 1 | Scope: X38-D-04 (Contamination Firewall)
Input: /var/www/trading-bots/btc-spot-dev/research/x38/debate/002-contamination-firewall/claude_code/round-1_opening-critique.md
Output: /var/www/trading-bots/btc-spot-dev/research/x38/debate/002-contamination-firewall/codex/round-1_rebuttal.md

Read Prompt A in `debate/prompt_template.md` for the canonical round structure.

HEADER (mandatory):
  # Round 1 — Rebuttal: Contamination Firewall
  **Topic**: 002 — Contamination Firewall
  **Author**: codex
  **Date**: 2026-03-25
  **Responds to**: `claude_code/round-1_opening-critique.md`
  **Scope**: X38-D-04 (F-04: Contamination firewall — machine-enforced)
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
- Git root: `/var/www/trading-bots/btc-spot-dev/research/x38/`
- Shared Python root: `/var/www/trading-bots/`
- Do not assume `/var/www/trading-bots/` or `/var/www/trading-bots/btc-spot-dev/` is the git root.

Task:
- Review X38-D-04 and its sub-questions (Findings A-D from
  input_f06_category_coverage.md) as facets of the single issue.
- Give each facet a verdict, but put the most depth on the arguments
  that could actually change the design.
- Key battlegrounds for this topic:
  (a) Category gap: 5th category (STRUCTURAL_PRIOR) vs redefine existing?
  (b) PROVENANCE_AUDIT_SERIALIZATION overload: split or keep?
  (c) STOP_DISCIPLINE thinness: consolidate into ANTI_PATTERN?
  (d) State machine complexity: appropriate for v1?
  (e) MK-14 interface: firewall enforcement vs legitimate MK updates?
- For each facet addressed: classification + evidence pointer + critique.
- Split verdicts are allowed, for example:
  "accept observation, reject mechanism".
- End with the status table required by `debate/rules.md` §11.
```

---

MODE B - Rebuttal / Reviewer Reply

```
Role: Codex (reviewer / adversarial critic)
Round: 6 | Scope: X38-D-04 (Contamination Firewall)
Input: /var/www/trading-bots/btc-spot-dev/research/x38/debate/002-contamination-firewall/claude_code/round-6_author-reply.md
Output: /var/www/trading-bots/btc-spot-dev/research/x38/debate/002-contamination-firewall/codex/round-6_reviewer-reply.md

Read Prompt B in `debate/prompt_template.md` for the canonical round structure.
If this prompt conflicts with canonical x38 sources, canonical sources win.

HEADER (mandatory):
  # Round 6 — Reviewer Reply: Contamination Firewall
  **Topic**: 002 — Contamination Firewall
  **Author**: codex
  **Date**: 2026-03-25
  **Responds to**: `claude_code/round-6_author-reply.md`
  **Scope**: X38-D-04 (F-04: Contamination firewall — machine-enforced)
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
- Git root: `/var/www/trading-bots/btc-spot-dev/research/x38/`
- Shared Python root: `/var/www/trading-bots/`
- Do not assume `/var/www/trading-bots/` or `/var/www/trading-bots/btc-spot-dev/` is the git root.

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
Task: Judgment-call memo for debate/002-contamination-firewall/, after Round {ROUND_NUM}
Scope: X38-D-04 (F-04: Contamination firewall — machine-enforced)
Output: /var/www/trading-bots/btc-spot-dev/research/x38/debate/002-contamination-firewall/codex/judgment-call-memo.md
Read-only — do not modify existing files.

Additionally read all round files in:
  - debate/002-contamination-firewall/claude_code/
  - debate/002-contamination-firewall/codex/

Produce:

1. PER-ISSUE SUMMARY
   | Issue ID | Finding | Final positions | Agreement level | Recommended resolution |

   Issue: X38-D-04 (single finding, multiple facets from MK-07 investigation)

   Facets to assess separately:
   - F-04 core: typed schema + whitelist + state machine + filesystem enforcement
   - Finding A: category gap (~10 Tier 2 structural priors homeless)
   - Finding B: MK-07 interim rule blocks admissible rules
   - Finding C: STOP_DISCIPLINE thinness (3 rules)
   - Finding D: PROVENANCE_AUDIT_SERIALIZATION overload (~25+ rules)

   Agreement levels:
   - Converged: §7(a)(b)(c) complete
   - Near-converged: substantive agreement, §7 incomplete
   - Disputed: genuine disagreement remains

   For near-converged or disputed facets, state both positions with evidence
   pointers. For judgment calls, state the tradeoff clearly and do not pick a
   winner.

2. STEEL-MAN AUDIT
   - Which facets completed §7(a)(b)(c)?
   - Which facets still have incomplete steel-man?

3. MK-07 RESOLUTION CHECK
   - Did debate produce a final fix for the ~10 Tier 2 structural priors gap?
   - Is UNMAPPED tag retired or made permanent?
   - Is the MK-07 addendum in Topic 004 final-resolution.md consistent with
     the debate outcome?

4. STATUS DRIFT CHECK
   - Compare `findings-under-review.md` against actual round outcomes.
   - Flag discrepancies for human resolution.

Do not:
  - make final decisions
  - propose "consensus" or "compromise" positions
  - write to any file other than the output path above
```
