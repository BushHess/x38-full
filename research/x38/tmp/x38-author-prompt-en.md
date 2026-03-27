# x38 Claude Code Debate Author — Format Supplement

## Mode A — Opening Critique (format only)

```
Role: Claude Code (architect / opening critic)
Mode: opening | Round: 1 | Scope: CA-01, CA-02, SSE-09, SSE-04-THR (Convergence Analysis)
Output: /var/www/trading-bots/btc-spot-dev/research/x38/debate/013-convergence-analysis/claude_code/round-1_opening-critique.md

HEADER (mandatory):
  # Round 1 — Opening Critique: Convergence Analysis
  **Topic**: 013-convergence-analysis
  **Author**: claude_code
  **Date**: 2026-03-27
  **Scope**: CA-01 (Convergence measurement framework),
             CA-02 (Stop conditions & diminishing returns),
             SSE-09 (Scan-phase correction law default),
             SSE-04-THR (Equivalence + anomaly thresholds)
  **Input documents**: (list all files read)

ENVIRONMENT REMINDER:
- Follow `research/x38/AGENTS.md` for repo/environment boundaries.
- Main working directory: `/var/www/trading-bots/btc-spot-dev/research/x38/`
- Git root: `/var/www/trading-bots/btc-spot-dev/`
- Shared Python root: `/var/www/trading-bots/`
- Do not assume `/var/www/trading-bots/` is the git root. Git root is `/var/www/trading-bots/btc-spot-dev/`.

PREAMBLE (2-4 paragraphs):
  - Establish architect role
  - State burden of proof (→ rules.md §5)
  - Critical context + scope boundaries
  - Note: Topic 013 has 4 findings: 2 original (CA-01, CA-02) + 2 routed
    from Topic 018 (SSE-09, SSE-04-THR). Routed issues carry architectural
    context from Topic 018 closure (CLOSED 2026-03-27, standard 2-agent
    debate). Debate each finding independently.

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
Mode: reply | Round: 4 | Scope: CA-01, CA-02, SSE-09, SSE-04-THR (Convergence Analysis)
Input: /var/www/trading-bots/btc-spot-dev/research/x38/debate/013-convergence-analysis/claude_code/round-3_author-reply.md
Output: /var/www/trading-bots/btc-spot-dev/research/x38/debate/013-convergence-analysis/claude_code/round-4_author-reply.md

Read Prompt B in `debate/prompt_template.md` for the canonical round structure.
If this prompt conflicts with canonical x38 sources, canonical sources win.

HEADER (mandatory):
  # Round 4 — Author Reply: Convergence Analysis
  **Topic**: 013 — Convergence Analysis
  **Author**: claude_code
  **Date**: 2026-03-27
  **Responds to**: `codex/round-3_reviewer-reply.md`
  **Scope**: CA-01, CA-02, SSE-09, SSE-04-THR

MANDATORY RULE REMINDER:
    1. §4: Attack the argument, not the conclusion.
    2. §7: Steel-man is required before marking `Converged`.
    3. §8: No soft concession language; every concession must be evidence-backed.
    4. §12: No new topic creation after round 1.

ENVIRONMENT REMINDER:
- Follow `research/x38/AGENTS.md` for repo/environment boundaries.
- Main working directory: `/var/www/trading-bots/btc-spot-dev/research/x38/`
- Git root: `/var/www/trading-bots/btc-spot-dev/`
- Shared Python root: `/var/www/trading-bots/`
- Do not assume `/var/www/trading-bots/` is the git root. Git root is `/var/www/trading-bots/btc-spot-dev/`.

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
Mode: closure | Scope: CA-01, CA-02, SSE-09, SSE-04-THR (Convergence Analysis)
Topic: 013 — Convergence Analysis

ENVIRONMENT REMINDER:
- Follow `research/x38/AGENTS.md` for repo/environment boundaries.
- Main working directory: `/var/www/trading-bots/btc-spot-dev/research/x38/`
- Git root: `/var/www/trading-bots/btc-spot-dev/`
- Shared Python root: `/var/www/trading-bots/`
- Do not assume `/var/www/trading-bots/` is the git root. Git root is `/var/www/trading-bots/btc-spot-dev/`.

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
  Path: debate/013-convergence-analysis/final-resolution.md
  Use Template D (prompt_template.md). Include:
  - Decisions table: CA-01, CA-02, SSE-09, SSE-04-THR with
    Resolution, Type, Round closed
  - Key design decisions (for drafts/):
    - Convergence measurement framework (distance metrics, statistical tests,
      multi-level convergence granularity)
    - Stop conditions & diminishing returns (within-campaign, cross-campaign,
      MK-17 shadow-only interaction)
    - Scan-phase correction law default (Holm/FDR/cascade, v1 recommendation)
    - Equivalence + anomaly thresholds (behavioral ρ cutoff, structural hash
      granularity, anomaly axis thresholds)
  - Unresolved tradeoffs (for human review)
  - Cross-topic impact: Topic 017 (coverage metrics, budget governor),
    Topic 003 (pipeline stop logic), Topic 008 (identity vocabulary compatibility)
  - Draft impact table

STEP 2 — UPDATE `findings-under-review.md`:
  Path: debate/013-convergence-analysis/findings-under-review.md
  - Update `current_status` for each issue (Converged / Judgment call)
  - Record round and date closed
  - Do NOT create ad-hoc fields — use existing schema only

STEP 3 — UPDATE `debate-index.md` + topic `README.md`:
  - Change topic 013 status → CLOSED
  - Sync summary with final-resolution.md

STEP 3b — Sync closure status across global files:
    Files: PLAN.md, EXECUTION_PLAN.md, docs/evidence_coverage.md
    - Update topic status OPEN → CLOSED in all status/topic tables
    - Update debate round counts and topics-remaining counts
    - Add closure reference in PLAN.md near the relevant section
      (blockquote: date, rounds, resolution summary, dependency list)

STEP 3c — Check downstream unblocking:
    Topic 013 closure may unblock:
    - Topic 017 (epistemic search policy) — hard-dep on 013 (convergence/stop conditions)
    - Topic 003 (protocol engine) — indirect via 017
    Update EXECUTION_PLAN.md dependency notes if applicable.

STEP 4 — CREATE/UPDATE draft spec in `drafts/`:
  - Convert converged design decisions to spec sections
  - Each decision must trace: Issue ID → final-resolution.md → evidence
  - methodology_spec.md is the primary target (convergence algorithm, stop conditions)
  - architecture_spec.md secondary (correction law, equivalence thresholds)

STEP 5 — VERIFY no status drift:
  - README.md, debate-index.md, EXECUTION_PLAN.md all reflect 013 = CLOSED
  - No orphaned Open issues remain in findings-under-review.md

Nếu còn bước nào nữa mà tôi chưa nêu ra, hãy nhắc tôi bổ sung.
```
