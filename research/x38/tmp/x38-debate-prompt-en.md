# x38 Codex Debate Reviewer - Prompt

MODE A - Opening Critique

```
Role: Codex (reviewer / adversarial critic)
Round: 1 | Scope: X38-D-02, X38-D-09, X38-D-13, X38-SSE-04-IDV (Architecture Pillars & Identity)
Input: /var/www/trading-bots/btc-spot-dev/research/x38/debate/008-architecture-identity/claude_code/round-1_opening-critique.md
Output: /var/www/trading-bots/btc-spot-dev/research/x38/debate/008-architecture-identity/codex/round-1_rebuttal.md

Read Prompt A in `debate/prompt_template.md` for the canonical round structure.

HEADER (mandatory):
  # Round 1 — Rebuttal: Architecture Pillars & Identity
  **Topic**: 008 — Architecture Pillars & Identity
  **Author**: codex
  **Date**: 2026-03-26
  **Responds to**: `claude_code/round-1_opening-critique.md`
  **Scope**: X38-D-02 (Three pillars), X38-D-09 (Directory structure),
             X38-D-13 (Three-identity-axis model), X38-SSE-04-IDV (Candidate-level identity vocabulary)
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
- Review X38-D-02, X38-D-09, X38-D-13, X38-SSE-04-IDV as four separate issues
  (not facets of a single finding).
- Give each issue a verdict, but put the most depth on the arguments
  that could actually change the design.
- Key battlegrounds for this topic:
  (a) F-02: Three pillars sufficiency — 3 enough or need 4th?
      ESP (Topic 017) as sub-component vs architectural pillar?
      Meta-Updater scope: methodology-level only? What counts as contamination?
      Reproducibility/audit trail: already covered by Protocol Engine or separate?
  (b) F-09: Directory structure — knowledge/ at root vs src/?
      Data in-project copies vs external path? Venv riêng vs shared?
      campaigns/ as sole growth axis — scalability implications?
  (c) F-13: Three-identity-axis model — 3 axes (constitution, program, system)
      vs 2 axes (campaign + session)? When does protocol_version change?
      Governance review weight? Cross-protocol convergence analysis rules?
  (d) SSE-04-IDV: Candidate-level equivalence vocabulary — belongs in 008 (identity)
      or 013 (convergence)? If 008: X38-D-13 scope expansion? Structural pre-bucket
      definition (descriptor hash, parameter family, AST-hash)?
- For each issue addressed: classification + evidence pointer + critique.
- Split verdicts are allowed, for example:
  "accept observation, reject mechanism".
- End with the status table required by `debate/rules.md` §11.
```

---

MODE B - Rebuttal / Reviewer Reply

```
Role: Codex (reviewer / adversarial critic)
Round: 2 | Scope: X38-D-02, X38-D-09, X38-D-13, X38-SSE-04-IDV (Architecture Pillars & Identity)
Input: /var/www/trading-bots/btc-spot-dev/research/x38/debate/008-architecture-identity/claude_code/round-2_author-reply.md
Output: /var/www/trading-bots/btc-spot-dev/research/x38/debate/008-architecture-identity/codex/round-2_reviewer-reply.md

Read Prompt B in `debate/prompt_template.md` for the canonical round structure.
If this prompt conflicts with canonical x38 sources, canonical sources win.

HEADER (mandatory):
  # Round 2 — Reviewer Reply: Architecture Pillars & Identity
  **Topic**: 008 — Architecture Pillars & Identity
  **Author**: codex
  **Date**: 2026-03-26
  **Responds to**: `claude_code/round-2_author-reply.md`
  **Scope**: X38-D-02, X38-D-09, X38-D-13, X38-SSE-04-IDV
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
Task: Judgment-call memo for debate/008-architecture-identity/, after Round {ROUND_NUM}
Scope: X38-D-02, X38-D-09, X38-D-13, X38-SSE-04-IDV
Output: /var/www/trading-bots/btc-spot-dev/research/x38/debate/008-architecture-identity/codex/judgment-call-memo.md
Read-only — do not modify existing files.

Additionally read all round files in:
  - debate/008-architecture-identity/claude_code/
  - debate/008-architecture-identity/codex/

Produce:

1. PER-ISSUE SUMMARY
   | Issue ID | Finding | Final positions | Agreement level | Recommended resolution |

   Issues to assess separately:
   - X38-D-02: Three pillars sufficiency (3 vs 4, ESP as sub-component vs pillar,
     Meta-Updater scope boundaries, reproducibility/audit trail coverage)
   - X38-D-09: Directory structure (knowledge/ placement, data/ location,
     venv policy, campaigns/ growth model, docs/ necessity)
   - X38-D-13: Three-identity-axis model (3 axes vs 2, protocol_version trigger,
     governance review weight, cross-protocol convergence rules)
   - X38-SSE-04-IDV: Candidate-level identity vocabulary (scope ownership 008 vs 013,
     structural pre-bucket definition, interaction with SSE-D-06 hybrid equivalence)

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
   - Topic 017 (epistemic search policy): does pillar decision (F-02) affect
     whether ESP becomes a 4th pillar or Protocol Engine sub-component?
   - Topic 015 (artifact versioning): does identity model (F-13) create
     protocol_version dependency for artifact invalidation rules?
   - Topic 013 (convergence analysis): does candidate vocabulary (SSE-04-IDV)
     ownership affect convergence measurement? Cross-protocol comparison rules?
   - Topic 009 (data integrity): does directory structure (F-09) constrain
     data location or immutability enforcement?

4. STATUS DRIFT CHECK
   - Compare `findings-under-review.md` against actual round outcomes.
   - Flag discrepancies for human resolution.

Do not:
  - make final decisions
  - propose "consensus" or "compromise" positions
  - write to any file other than the output path above
```
