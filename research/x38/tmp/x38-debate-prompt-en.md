# x38 Codex Debate Reviewer - Prompt

MODE A - Opening Critique

```
Role: Codex (reviewer / adversarial critic)
Round: 1 | Scope: SSE-D-01, SSE-D-02/03, SSE-D-04, SSE-D-05, SSE-D-06, SSE-D-07, SSE-D-08, SSE-D-09, SSE-D-10, SSE-D-11 (Search-Space Expansion)
Input: /var/www/trading-bots/btc-spot-dev/research/x38/debate/018-search-space-expansion/claude_code/round-1_opening-critique.md
Output: /var/www/trading-bots/btc-spot-dev/research/x38/debate/018-search-space-expansion/codex/round-1_rebuttal.md

Read Prompt A in `debate/prompt_template.md` for the canonical round structure.

HEADER (mandatory):
  # Round 1 — Rebuttal: Search-Space Expansion
  **Topic**: 018 — Search-Space Expansion
  **Author**: codex
  **Date**: 2026-03-27
  **Responds to**: `claude_code/round-1_opening-critique.md`
  **Scope**: SSE-D-01 (Lane ownership), SSE-D-02/03 (Bounded ideation / cold-start),
             SSE-D-04 (Breadth-expansion contract), SSE-D-05 (Surprise lane),
             SSE-D-06 (Cell + equivalence), SSE-D-07 (3-layer lineage),
             SSE-D-08 (Contradiction memory), SSE-D-09 (Multiplicity control),
             SSE-D-10 (Domain-seed hook), SSE-D-11 (APE v1 scope)
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
- Review all 10 OIs (SSE-D-01 through SSE-D-11) as independent issues.
- Prior 4-agent debate (extra-canonical) serves as input evidence, not binding.
  Evidence archive: `docs/search-space-expansion/debate/`.
- Give each OI a verdict, but put the most depth on the arguments
  that could actually change the design.
- Key battlegrounds for this topic:
  (a) SSE-D-01: Lane ownership — fold discovery into 6 existing topics
      or keep Topic 018 umbrella? Object boundary clarity?
  (b) SSE-D-02/03: Bounded ideation — 4 hard rules sufficient?
      Grammar depth-1 seed as default vs registry_only? Cold-start activation conditions?
  (c) SSE-D-04: Breadth-expansion interface — 7-field contract completeness?
      Protocol must declare all 7 before breadth activation — enforceable?
  (d) SSE-D-05: Surprise lane — recognition topology (surprise_queue →
      equivalence_audit → proof_bundle → freeze). 5 anomaly axes sufficient?
  (e) SSE-D-06: Hybrid equivalence — deterministic structural pre-bucket +
      behavioral nearest-rival audit. No LLM judge. Method soundness?
  (f) SSE-D-07: 3-layer lineage — semantic split (feature_lineage,
      candidate_genealogy, proposal_provenance). Routing to Topic 015 correct?
  (g) SSE-D-08: Contradiction memory — descriptor-level, shadow-only (MK-17).
      Storage → 015, consumption → 017. Split routing correct?
  (h) SSE-D-09: Multiplicity control — breadth coupling via SSE-D-04 field 5.
      Routing to Topic 013 correct?
  (i) SSE-D-10: Domain-seed hook — optional provenance, no replay semantics.
      Sufficient or needs stronger contract?
  (j) SSE-D-11: APE v1 scope — template parameterization only, no free-form
      code generation. Scope boundary correct?
- For each issue addressed: classification + evidence pointer + critique.
- Split verdicts are allowed, for example:
  "accept observation, reject mechanism".
- End with the status table required by `debate/rules.md` §11.
```

---

MODE B - Rebuttal / Reviewer Reply

```
Role: Codex (reviewer / adversarial critic)
Round: 4 | Scope: SSE-D-01, SSE-D-02/03, SSE-D-04, SSE-D-05, SSE-D-06, SSE-D-07, SSE-D-08, SSE-D-09, SSE-D-10, SSE-D-11 (Search-Space Expansion)
Input: /var/www/trading-bots/btc-spot-dev/research/x38/debate/018-search-space-expansion/claude_code/round-4_author-reply.md
Output: /var/www/trading-bots/btc-spot-dev/research/x38/debate/018-search-space-expansion/codex/round-4_reviewer-reply.md

Read Prompt B in `debate/prompt_template.md` for the canonical round structure.
If this prompt conflicts with canonical x38 sources, canonical sources win.

HEADER (mandatory):
  # Round 4 — Reviewer Reply: Search-Space Expansion
  **Topic**: 018 — Search-Space Expansion
  **Author**: codex
  **Date**: 2026-03-27
  **Responds to**: `claude_code/round-4_author-reply.md`
  **Scope**: SSE-D-01, SSE-D-02/03, SSE-D-04, SSE-D-05, SSE-D-06, SSE-D-07, SSE-D-08, SSE-D-09, SSE-D-10, SSE-D-11
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
Task: Judgment-call memo for debate/018-search-space-expansion/, after Round {ROUND_NUM}
Scope: SSE-D-01, SSE-D-02/03, SSE-D-04, SSE-D-05, SSE-D-06, SSE-D-07, SSE-D-08, SSE-D-09, SSE-D-10, SSE-D-11
Output: /var/www/trading-bots/btc-spot-dev/research/x38/debate/018-search-space-expansion/codex/judgment-call-memo.md
Read-only — do not modify existing files.

Additionally read all round files in:
  - debate/018-search-space-expansion/claude_code/
  - debate/018-search-space-expansion/codex/
Additionally read prior extra-canonical evidence:
  - docs/search-space-expansion/debate/ (4-agent archive, non-authoritative)

Produce:

1. PER-ISSUE SUMMARY
   | Issue ID | Finding | Final positions | Agreement level | Recommended resolution |

   Issues to assess separately:
   - SSE-D-01: Pre-lock generation lane ownership (fold into 6 topics vs umbrella)
   - SSE-D-02/03: Bounded ideation + conditional cold-start (4 hard rules, 2 generation modes)
   - SSE-D-04: Breadth-expansion interface contract (7-field completeness)
   - SSE-D-05: Surprise lane / recognition inventory (topology, 5 anomaly axes)
   - SSE-D-06: Cell + equivalence + correction method (hybrid: structural + behavioral)
   - SSE-D-07: 3-layer lineage (semantic split, routing → 015)
   - SSE-D-08: Cross-campaign contradiction memory (shadow-only, routing → 015/017)
   - SSE-D-09: Multiplicity control (breadth coupling, routing → 013)
   - SSE-D-10: Domain-seed hook (optional provenance, no replay)
   - SSE-D-11: APE v1 scope (template parameterization only)

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
   - Topic 006 (feature engine): does generation_mode (SSE-D-03) affect
     registry acceptance of auto-generated features?
   - Topic 015 (artifact versioning): do lineage (SSE-D-07) and contradiction
     registry (SSE-D-08) create new invalidation rules?
   - Topic 017 (epistemic search policy): does surprise topology (SSE-D-05) and
     contradiction consumption (SSE-D-08-CON) affect ESP scope?
   - Topic 013 (convergence analysis): does multiplicity control (SSE-D-09)
     affect correction formula and breadth-expansion accounting?
   - Topic 008 (architecture identity): does identity_vocabulary (SSE-D-04 field 3)
     interact with X38-D-13 candidate-level vocabulary?
   - Topic 003 (protocol engine): does breadth-activation blocker (SSE-D-04)
     affect stage wiring or protocol_lock enforcement?

4. STATUS DRIFT CHECK
   - Compare `findings-under-review.md` against actual round outcomes.
   - Flag discrepancies for human resolution.

Do not:
  - make final decisions
  - propose "consensus" or "compromise" positions
  - write to any file other than the output path above
```
