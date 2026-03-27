# x38 Claude Code Debate Author — Format Supplement

## Mode A — Opening Critique (format only)

```
Role: Claude Code (architect / opening critic)
Mode: opening | Round: 1 | Scope: SSE-D-01, SSE-D-02/03, SSE-D-04, SSE-D-05, SSE-D-06, SSE-D-07, SSE-D-08, SSE-D-09, SSE-D-10, SSE-D-11 (Search-Space Expansion)
Output: /var/www/trading-bots/btc-spot-dev/research/x38/debate/018-search-space-expansion/claude_code/round-1_opening-critique.md

HEADER (mandatory):
  # Round 1 — Opening Critique: Search-Space Expansion
  **Topic**: 018-search-space-expansion
  **Author**: claude_code
  **Date**: 2026-03-27
  **Scope**: SSE-D-01 (Lane ownership), SSE-D-02/03 (Bounded ideation / cold-start),
             SSE-D-04 (Breadth-expansion contract), SSE-D-05 (Surprise lane),
             SSE-D-06 (Cell + equivalence), SSE-D-07 (3-layer lineage),
             SSE-D-08 (Contradiction memory), SSE-D-09 (Multiplicity control),
             SSE-D-10 (Domain-seed hook), SSE-D-11 (APE v1 scope)
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
  - Note: Topic 018 has 10 OIs (SSE-D-01 through SSE-D-11), each with
    its own issue ID. Prior 4-agent debate (extra-canonical) serves as
    input evidence. Standard 2-agent re-debate required per x38_RULES.md §5.
    Debate each OI independently; prior Converged status is non-authoritative.

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
Mode: reply | Round: 4 | Scope: SSE-D-01, SSE-D-02/03, SSE-D-04, SSE-D-05, SSE-D-06, SSE-D-07, SSE-D-08, SSE-D-09, SSE-D-10, SSE-D-11 (Search-Space Expansion)
Input: /var/www/trading-bots/btc-spot-dev/research/x38/debate/018-search-space-expansion/codex/round-3_reviewer-reply.md
Output: /var/www/trading-bots/btc-spot-dev/research/x38/debate/018-search-space-expansion/claude_code/round-4_author-reply.md

Read Prompt B in `debate/prompt_template.md` for the canonical round structure.
If this prompt conflicts with canonical x38 sources, canonical sources win.

HEADER (mandatory):
  # Round 4 — Author Reply: Search-Space Expansion
  **Topic**: 018 — Search-Space Expansion
  **Author**: claude_code
  **Date**: 2026-03-27
  **Responds to**: `codex/round-3_reviewer-reply.md`
  **Scope**: SSE-D-01, SSE-D-02/03, SSE-D-04, SSE-D-05, SSE-D-06, SSE-D-07, SSE-D-08, SSE-D-09, SSE-D-10, SSE-D-11

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
Mode: closure | Scope: SSE-D-01, SSE-D-02/03, SSE-D-04, SSE-D-05, SSE-D-06, SSE-D-07, SSE-D-08, SSE-D-09, SSE-D-10, SSE-D-11 (Search-Space Expansion)
Topic: 018 — Search-Space Expansion

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
  Path: debate/018-search-space-expansion/final-resolution.md
  Use Template D (prompt_template.md). Include:
  - Decisions table: SSE-D-01 through SSE-D-11 with
    Resolution, Type, Round closed
  - Key design decisions (for drafts/):
    - Lane ownership fold (018 umbrella vs downstream distribution)
    - Bounded ideation rules + cold-start activation (SSE-D-02/03)
    - Surprise lane recognition topology (SSE-D-05)
    - 3-layer lineage semantic split (SSE-D-07, routed → 015)
    - Contradiction memory: descriptor-level, shadow-only (SSE-D-08, routed → 015/017)
    - Breadth-expansion 7-field interface contract (SSE-D-04)
    - Domain-seed hook provenance (SSE-D-10)
    - Hybrid equivalence method (SSE-D-06)
    - Multiplicity control coupling (SSE-D-09, routed → 013)
    - APE v1 scope boundary (SSE-D-11)
  - Unresolved tradeoffs (for human review)
  - Cross-topic impact: Topic 006 (generation_mode), Topic 015 (lineage + invalidation),
    Topic 017 (surprise/proof integration), Topic 013 (multiplicity correction),
    Topic 008 (identity vocabulary), Topic 003 (breadth-activation blocker)
  - Draft impact table

STEP 2 — UPDATE `findings-under-review.md`:
  Path: debate/018-search-space-expansion/findings-under-review.md
  - Update `current_status` for each issue (Converged / Judgment call)
  - Record round and date closed
  - Do NOT create ad-hoc fields — use existing schema only

STEP 3 — UPDATE `debate-index.md` + topic `README.md`:
  - Change topic 018 status → CLOSED
  - Sync summary with final-resolution.md

STEP 3b — Sync closure status across global files:
    Files: PLAN.md, EXECUTION_PLAN.md, docs/evidence_coverage.md
    - Update topic status OPEN → CLOSED in all status/topic tables
    - Update debate round counts and topics-remaining counts
    - Add closure reference in PLAN.md near the relevant section
      (blockquote: date, rounds, resolution summary, dependency list)

STEP 3c — Check downstream unblocking:
    Topic 018 closure may unblock:
    - Topic 006 (feature engine) — SSE-D-03 generation_mode routing
    - Topic 015 (artifact versioning) — SSE-D-07/08 lineage + contradiction
    - Topic 017 (epistemic search policy) — SSE-D-05 topology + SSE-D-08-CON
    - Topic 013 (convergence analysis) — SSE-D-09 multiplicity control
    - Topic 008 (architecture identity) — SSE-D-04 identity_vocabulary
    - Topic 003 (protocol engine) — SSE-D-04 breadth-activation blocker
    Update EXECUTION_PLAN.md dependency notes if applicable.

STEP 4 — CREATE/UPDATE draft spec in `drafts/`:
  - Convert converged design decisions to spec sections
  - Each decision must trace: Issue ID → final-resolution.md → evidence
  - discovery_spec.md is the primary target (bounded ideation, surprise lane, APE)
  - architecture_spec.md secondary (breadth-expansion contract, lineage routing)

STEP 5 — VERIFY no status drift:
  - README.md, debate-index.md, EXECUTION_PLAN.md all reflect 018 = CLOSED
  - No orphaned Open issues remain in findings-under-review.md

Nếu còn bước nào nữa mà tôi chưa nêu ra, hãy nhắc tôi bổ sung.
```
