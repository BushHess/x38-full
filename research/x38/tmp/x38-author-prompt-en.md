# x38 Claude Code Debate Author — Format Supplement

## Mode A — Opening Critique (format only)

```
Role: Claude Code (architect / opening critic)
Mode: opening | Round: 1 | Scope: X38-D-04 (Contamination Firewall)
Output: /var/www/trading-bots/btc-spot-dev/research/x38/debate/002-contamination-firewall/claude_code/round-1_opening-critique.md

HEADER (mandatory):
  # Round 1 — Opening Critique: Contamination Firewall
  **Topic**: 002-contamination-firewall
  **Author**: claude_code
  **Date**: 2026-03-25
  **Scope**: X38-D-04 (F-04: Contamination firewall — machine-enforced)
  **Input documents**: (list all files read)

ENVIRONMENT REMINDER:
- Follow `research/x38/AGENTS.md` for repo/environment boundaries.
- Main working directory: `/var/www/trading-bots/btc-spot-dev/research/x38/`
- Git root: `/var/www/trading-bots/btc-spot-dev/research/x38/`
- Shared Python root: `/var/www/trading-bots/`
- Do not assume `/var/www/trading-bots/` or `/var/www/trading-bots/btc-spot-dev/` is the git root.

PREAMBLE (2-4 paragraphs):
  - Establish architect role
  - State burden of proof (→ rules.md §5)
  - Critical context + scope boundaries
  - Note: F-04 is a single finding but with multiple sub-questions from MK-07
    investigation (input_f06_category_coverage.md). Sub-questions (Findings A-D)
    are debated as facets of F-04, not separate issues.

PER-ISSUE (for each Open issue):
  ## {Issue ID}: {Title} — {ACCEPT/REJECT/SPLIT/DEFER to V2+}
  ### Position
  [1-3 paragraphs] + **Key argument** + Evidence + **However** + **Proposed amendment**
  ### Classification: [Sai thiết kế | Thiếu sót | Judgment call]

SUMMARY:
  ### Accepted (near-convergence candidates)
  ### Challenged (need debate)

STATUS TABLE: per rules.md §11.
```

---

## Mode B — Author Reply (format only)

```
Role: Claude Code (architect / author)
Mode: reply | Round: 6 | Scope: X38-D-04 (Contamination Firewall)
Input: /var/www/trading-bots/btc-spot-dev/research/x38/debate/002-contamination-firewall/codex/round-5_reviewer-reply.md
Output: /var/www/trading-bots/btc-spot-dev/research/x38/debate/002-contamination-firewall/claude_code/round-6_author-reply.md

Read Prompt B in `debate/prompt_template.md` for the canonical round structure.
If this prompt conflicts with canonical x38 sources, canonical sources win.

HEADER (mandatory):
  # Round 6 — Author Reply: Contamination Firewall
  **Topic**: 002 — Contamination Firewall
  **Author**: claude_code
  **Date**: 2026-03-25
  **Responds to**: `codex/round-5_reviewer-reply.md`
  **Scope**: X38-D-04 (F-04: Contamination firewall — machine-enforced)

MANDATORY RULE REMINDER:
    1. §4: Attack the argument, not the conclusion.
    2. §7: Steel-man is required before marking `Converged`.
    3. §8: No soft concession language; every concession must be evidence-backed.
    4. §12: No new topic creation after round 1.

ENVIRONMENT REMINDER:
- Follow `research/x38/AGENTS.md` for repo/environment boundaries.
- Main working directory: `/var/www/trading-bots/btc-spot-dev/research/x38/`
- Git root: `/var/www/trading-bots/btc-spot-dev/research/x38/`
- Shared Python root: `/var/www/trading-bots/`
- Do not assume `/var/www/trading-bots/` or `/var/www/trading-bots/btc-spot-dev/` is the git root.

PART A — STEEL-MAN ATTEMPTS (issues moving toward agreement):
  ### {Issue ID}: {Title}
  **Steel-man for opposing position** ({brief statement}):
  [2-3 sentences: strongest case for Codex's position]
  **Why the steel-man does not hold**:
  1. [counter-argument with evidence]
  2. [concrete counterexample]
  **Conclusion**: [verdict]
  **Proposed status**: Converged — waiting for Codex to confirm (§7c).

PART B — CONTINUED DEBATE (issues still Open):
  - Address Codex's specific counter-arguments
  - New evidence or refined argument
  - Split verdicts where warranted

STATUS TABLE: updated per rules.md §11.
```

---

## Mode C — Closure (format only)

```
Role: Claude Code (architect / closure)
Mode: closure | Scope: X38-D-04 (Contamination Firewall)
Topic: 002 — Contamination Firewall

ENVIRONMENT REMINDER:
- Follow `research/x38/AGENTS.md` for repo/environment boundaries.
- Main working directory: `/var/www/trading-bots/btc-spot-dev/research/x38/`
- Git root: `/var/www/trading-bots/btc-spot-dev/research/x38/`
- Shared Python root: `/var/www/trading-bots/`
- Do not assume `/var/www/trading-bots/` or `/var/www/trading-bots/btc-spot-dev/` is the git root.

If this prompt conflicts with canonical x38 sources, canonical sources win.

PREREQUISITES (verify before proceeding):
  - ALL issues in scope must be Converged or Judgment call
  - Human researcher has decided all Judgment calls
  - Codex closure audit should be complete
  - ROUND SYMMETRY CHECK (rules.md §14b): both agents must have equal
    round counts, OR the asymmetry must be documented with justification.
    If author submitted round N but reviewer has not responded:
    (a) Run reviewer's round N before closure, OR
    (b) Document why asymmetry is acceptable in final-resolution.md
        (e.g., "all issues already Converged before round N",
         "human Judgment call is independent of both agent positions")
    Skipping this check risks closing without the reviewer's response
    to the author's final arguments.

STEP 1 — CREATE `final-resolution.md`:
  Path: debate/002-contamination-firewall/final-resolution.md
  Use Template D (prompt_template.md). Include:
  - Decisions table: X38-D-04 with Resolution, Type, Round closed
  - Key design decisions (for drafts/): typed schema, whitelist categories
    (including MK-07 gap resolution), state machine, filesystem enforcement
  - MK-07 final fix status: did debate resolve the ~10 Tier 2 structural
    priors gap? If yes, specify new category or redefinition. If no,
    document permanent governance path for UNMAPPED rules.
  - Unresolved tradeoffs (for human review)
  - Cross-topic impact: MK-14 interface, Topic 009 enforcement overlap,
    Topic 016 recalibration compatibility, Topic 017 phenotype layer
  - Draft impact table

STEP 2 — UPDATE `findings-under-review.md`:
  Path: debate/002-contamination-firewall/findings-under-review.md
  - Update `current_status` for X38-D-04 (Converged / Judgment call)
  - Record round and date closed
  - Do NOT create ad-hoc fields — use existing schema only

STEP 3 — UPDATE `debate-index.md` + topic `README.md`:
  - Change topic 002 status → CLOSED
  - Sync summary with final-resolution.md

STEP 3b — Sync closure status across global files:
    Files: PLAN.md, EXECUTION_PLAN.md, docs/evidence_coverage.md
    - Update topic status OPEN → CLOSED in all status/topic tables
    - Update debate round counts and topics-remaining counts
    - Add closure reference in PLAN.md near the relevant section
      (blockquote: date, rounds, resolution summary, dependency list)

STEP 3c — Update Topic 004 MK-07 amendment (if applicable):
    If debate resolved the category gap:
    - Update 004-meta-knowledge/final-resolution.md MK-07 addendum
      to reference the 002 resolution (retire UNMAPPED tag or confirm
      permanent governance path)
    If not resolved (deferred to v2+):
    - Document in final-resolution.md that MK-07 UNMAPPED remains

STEP 4 — CREATE/UPDATE draft spec in `drafts/`:
  - Convert converged design decisions to spec sections
  - Each decision must trace: Issue ID → final-resolution.md → evidence

STEP 5 — VERIFY no status drift:
  - README.md, debate-index.md, EXECUTION_PLAN.md all reflect 002 = CLOSED
  - No orphaned Open issues remain in findings-under-review.md

Nếu còn bước nào nữa mà tôi chưa nêu ra, hãy nhắc tôi bổ sung.
```
