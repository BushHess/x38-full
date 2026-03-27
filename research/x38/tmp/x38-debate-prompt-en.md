# x38 Codex Debate Reviewer - Prompt

MODE A - Opening Critique

```
Role: Codex (reviewer / adversarial critic)
Round: 1 | Scope: CA-01, CA-02, SSE-09, SSE-04-THR (Convergence Analysis)
Input: /var/www/trading-bots/btc-spot-dev/research/x38/debate/013-convergence-analysis/claude_code/round-1_opening-critique.md
Output: /var/www/trading-bots/btc-spot-dev/research/x38/debate/013-convergence-analysis/codex/round-1_rebuttal.md

Read Prompt A in `debate/prompt_template.md` for the canonical round structure.

HEADER (mandatory):
  # Round 1 — Rebuttal: Convergence Analysis
  **Topic**: 013 — Convergence Analysis
  **Author**: codex
  **Date**: 2026-03-27
  **Responds to**: `claude_code/round-1_opening-critique.md`
  **Scope**: CA-01 (Convergence measurement framework),
             CA-02 (Stop conditions & diminishing returns),
             SSE-09 (Scan-phase correction law default),
             SSE-04-THR (Equivalence + anomaly thresholds)
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
- Review all 4 findings (CA-01, CA-02, SSE-09, SSE-04-THR) as independent issues.
- 2 original findings (CA-01, CA-02) from gap analysis. 2 routed from
  Topic 018 (SSE-09, SSE-04-THR) — CLOSED 2026-03-27, architectural context
  available in `debate/018-search-space-expansion/final-resolution.md`.
- Give each finding a verdict, but put the most depth on the arguments
  that could actually change the design.
- Key battlegrounds for this topic:
  (a) CA-01: Convergence measurement — granularity level (family vs
      param vs performance)? Distance metric (voting, Sharpe overlap,
      top-K Jaccard, rank correlation)? Statistical test (bootstrap,
      permutation, majority voting)? Multi-level convergence
      (FULLY_CONVERGED vs PARTIALLY_CONVERGED)?
  (b) CA-02: Stop conditions — within-campaign threshold (information gain,
      novel candidate rate, winner stability)? Cross-campaign same-data
      ceiling? MK-17 shadow-only interaction (accelerated diminishing
      returns)? Who decides to exceed ceilings (human only vs framework
      suggest)?
  (c) SSE-09: Scan-phase correction law — Holm (step-down) vs BH (FDR)
      vs cascade? Conservative vs balanced default for v1?
      Interaction with cell-elite diversity preservation?
  (d) SSE-04-THR: Equivalence + anomaly thresholds — behavioral ρ cutoff
      (0.95 vs 0.99)? Structural hash granularity for pre-bucketing?
      Anomaly axis thresholds (absolute vs relative to cell population)?
      Interaction with 006 feature family taxonomy?
- For each issue addressed: classification + evidence pointer + critique.
- Split verdicts are allowed, for example:
  "accept observation, reject mechanism".
- End with the status table required by `debate/rules.md` §11.
```

---

MODE B - Rebuttal / Reviewer Reply

```
Role: Codex (reviewer / adversarial critic)
Round: 2 | Scope: CA-01, CA-02, SSE-09, SSE-04-THR (Convergence Analysis)
Input: /var/www/trading-bots/btc-spot-dev/research/x38/debate/013-convergence-analysis/claude_code/round-2_author-reply.md
Output: /var/www/trading-bots/btc-spot-dev/research/x38/debate/013-convergence-analysis/codex/round-2_reviewer-reply.md

Read Prompt B in `debate/prompt_template.md` for the canonical round structure.
If this prompt conflicts with canonical x38 sources, canonical sources win.

HEADER (mandatory):
  # Round 2 — Reviewer Reply: Convergence Analysis
  **Topic**: 013 — Convergence Analysis
  **Author**: codex
  **Date**: 2026-03-27
  **Responds to**: `claude_code/round-2_author-reply.md`
  **Scope**: CA-01, CA-02, SSE-09, SSE-04-THR
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
Task: Judgment-call memo for debate/013-convergence-analysis/, after Round {ROUND_NUM}
Scope: CA-01, CA-02, SSE-09, SSE-04-THR
Output: /var/www/trading-bots/btc-spot-dev/research/x38/debate/013-convergence-analysis/codex/judgment-call-memo.md
Read-only — do not modify existing files.

Additionally read all round files in:
  - debate/013-convergence-analysis/claude_code/
  - debate/013-convergence-analysis/codex/
Additionally read prior routed-issue context:
  - debate/018-search-space-expansion/final-resolution.md (SSE-09, SSE-04-THR routing source)

Produce:

1. PER-ISSUE SUMMARY
   | Issue ID | Finding | Final positions | Agreement level | Recommended resolution |

   Issues to assess separately:
   - CA-01: Convergence measurement framework (distance metrics, statistical tests, multi-level convergence)
   - CA-02: Stop conditions & diminishing returns (within-campaign, cross-campaign, MK-17 interaction)
   - SSE-09: Scan-phase correction law default (Holm/FDR/cascade, v1 recommendation)
   - SSE-04-THR: Equivalence + anomaly thresholds (behavioral ρ cutoff, structural hash, anomaly axes)

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
   - Topic 017 (epistemic search policy): do convergence metrics (CA-01) and
     stop conditions (CA-02) affect ESP coverage obligations and budget governor?
   - Topic 003 (protocol engine): does the convergence algorithm affect pipeline
     stop logic and stage wiring?
   - Topic 008 (architecture identity): do equivalence thresholds (SSE-04-THR)
     interact with identity vocabulary (SSE-04-IDV)?

4. STATUS DRIFT CHECK
   - Compare `findings-under-review.md` against actual round outcomes.
   - Flag discrepancies for human resolution.

Do not:
  - make final decisions
  - propose "consensus" or "compromise" positions
  - write to any file other than the output path above
```
