# x38 Codex Repository Audit — Prompt Template

Supplementary prompt for OpenAI Codex (VSCode IDE) to audit the x38 research
repository for governance integrity, status consistency, and debate artifact health.

x38 is a **blueprint repository** — it produces architecture specs, not code.
Audit axes reflect this: the goal is debate/draft/publish readiness, not
"codebase health" or "implementation feasibility."

---

## Variables

| Variable | Required | Description | Example |
|---|---|---|---|
| `{REVIEW_SCOPE}` | yes | `full`, `quick`, or `maintenance` | `quick` |
| `{FOCUS_PATHS}` | quick/maint | Specific paths to audit | `debate/004-meta-knowledge/` |
| `{DIFF_RANGE}` | maintenance | Git range (default: `HEAD~5..HEAD`) | `HEAD~3..HEAD` |

---

## Audit Axes (priority order)

1. **Authority integrity** — topic dir content matches authority order in x38_RULES.md §4?
2. **Status drift** — final-resolution.md status matches README.md, debate-index.md, EXECUTION_PLAN.md?
3. **Debate artifact integrity** — round files sequenced? Status tables consistent across rounds?
4. **Draft/publish readiness** — closed topics have drafts started? Transitions valid?
5. **Terminology consistency** — same concept, same name across all files?
6. **Cascade impact** — recent changes break cross-references?

---

## Context Loading

```
1. If AGENTS.md was loaded by your environment, respect it.
   If not, read AGENTS.md first.
2. Read docs/online_vs_offline.md — mandatory doctrine for x38 design correctness.
3. Read x38_RULES.md — especially §3 (directory structure) and §4 (authority).
4. Read debate/rules.md — debate structure, naming conventions, extra-archive label (§18).
5. Read debate/debate-index.md — topic registry, wave structure, dependencies,
   convergence notes index. This is the source of truth for topic statuses and
   wave assignments.
6. Use open files / @file references as primary context.
7. When topic status matters, treat topic-dir artifacts and final-resolution.md
   as authoritative. Treat README.md, debate-index.md, and EXECUTION_PLAN.md
   as sync targets that may drift.
8. Valid topic statuses: OPEN | DEBATING | CLOSED | SPLIT.
   Read wave structure dynamically from debate-index.md; do not hardcode topic
   counts or wave membership from this template.
9. Do NOT inventory the whole repo unless a mismatch forces broader scan.
```

---

## General Guardrails

- Audit is hypothesis-driven for **discovery**, not for **scope determination**.
  Once a structural/compliance pattern is found, verify its scope across the
  full relevant denominator before publishing.
- Separate two objects of review:
  - **x38 governance findings**: repository/workflow/topic/publication state.
    These use `[BLOCK-*]`, `[WARNING]`, `[NOTE]`.
  - **Meta-audit observations**: audit-process issues such as mis-scoping,
    missing artifact trail, self-adjudication, vocabulary gaps, or unresolved
    interpretive disputes. Do not force these into workflow-impact labels.
- Representative examples do not prove exhaustive scope. For any cohort-wide,
  wave-wide, or class-wide claim, state the denominator and known exceptions.
- Before assigning any `[BLOCK-*]` label, explicitly test transition clauses,
  trigger conditions, and concurrency wording (`before`, `at`, `when starting`,
  etc.). If the trigger has not fired, default to readiness debt / non-blocking
  unless the authority text makes a present-tense block explicit.
- If the same actor both produces the original findings and adjudicates
  challenges, disclose self-adjudication as a methodological limitation.

---

## Mode: Full Audit

When: first review, before milestone, or after major restructuring.
Agent mode recommended. Subagents optional for parallel audit axes.

```
Role: Codex (governance auditor)
Scope: Full repository audit
Focus: {FOCUS_PATHS} (or entire repo if omitted)
Output:
- English report only.
- Do not modify x38 governance source files unless the human explicitly asks for remediation.
- Persist the final report to `audits/x38-audit-YYYY-MM-DD.md`. Creating/updating
  this audit artifact is allowed and expected.

After loading context:

- If a prior `audits/x38-audit-*.md` exists, compare findings and classify them as
  `NEW / RESOLVED / PERSISTING / REGRESSION`.
- Keep material correction history for audit-process disputes in:
  `Resolved Meta-Issues`, `Open Interpretive Disagreements`, or
  `Methodological Limitations`.

Axis 1 — AUTHORITY INTEGRITY:
- For each topic dir: does content align with x38_RULES.md §4?
  (published/ > topic dir > design_brief.md > PLAN.md)
- Are there documents claiming authority they don't have?
- Do docs/ files align with debate conclusions from closed topics?

Axis 2 — STATUS DRIFT:
- For each topic listed in debate-index.md:
  Compare authoritative artifact against sync targets:
  - CLOSED → final-resolution.md exists, all issues resolved
  - DEBATING → round files exist, no final-resolution.md
  - OPEN → findings-under-review.md exists, no round files (pre-debate)
  - SPLIT → topic decomposed, convergence notes retained, findings redistributed
  Check against: Topic README.md, debate-index.md entry, EXECUTION_PLAN.md phase.
- Verify debate-index.md finding counts match actual findings per topic.
- Verify EXECUTION_PLAN.md wave structure matches debate-index.md waves.
- Flag every discrepancy with exact file:line.
- If a discrepancy appears cohort-wide or wave-wide, verify the full denominator
  and known exceptions before publishing final scope.

Axis 3 — DEBATE ARTIFACT INTEGRITY:
- Round files named per rules.md naming conventions?
- Status tables in consecutive rounds show valid transitions?
- Steel-man protocols (§7) completed before Converged status?
- Topic dirs with round artifacts have findings-under-review.md entries?
- Pre-debate topic docs include mandatory sections from debate/rules.md
  (for example `Cross-topic tensions`), respecting any transition clauses.
- Topics with empty claude_code/ or codex/ subdirs: flag as pre-debate state (NOTE).
  Topics 013-016 may lack these subdirs entirely — also NOTE, not BLOCK.
- Issue ID prefixes: X38-MK-NN for topic 004, X38-D-NN for all others
  (inherited from topic 000 split — rules.md §Naming exception clause).
- Convergence note references (C-01→C-12) in sub-topic findings-under-review.md
  must resolve to 000-framework-proposal/findings-under-review.md.

Axis 4 — DRAFT/PUBLISH READINESS:
- Which topics are CLOSED (have final-resolution.md)?
- Do closed topics have drafts started in drafts/?
- Are draft → published transitions blocked by any open dependency?
  (Check debate-index.md Dependencies section.)
- Wave ordering respected? No Wave 3 topic (003, 014) debating/closed
  while upstream Wave 2 dependencies still OPEN.
- MK-14 (firewall boundary) resolved before meta_spec + architecture_spec
  drafts begin? (EXECUTION_PLAN.md constraint.)
- Before reporting `[BLOCK-DEBATE]`, `[BLOCK-DRAFT]`, or `[BLOCK-PUBLISH]`,
  confirm that the blocking trigger has actually fired rather than only being a
  future prerequisite or round-start task.

Axis 5 — TERMINOLOGY CONSISTENCY:
- Key terms with different meanings across files?
- Undefined jargon or acronyms?
- Naming consistent between claude_code/ and codex/ outputs?
- Topic statuses use exact labels: OPEN | DEBATING | CLOSED | SPLIT?
- Wave labels consistent: Wave 1 | Wave 2 | Wave 3?
- Finding IDs (F-01→F-33) and convergence note IDs (C-01→C-12): no gaps,
  no duplicates, consistent across topic assignments?

Axis 6 — STALE REFERENCES:
- References to removed artifacts? (e.g., tmp/final_convergence_map_v2.md)
- Cross-references to nonexistent files or wrong line numbers?
- Broken links between docs/ files?
- Prompt wrappers and canonical debate docs still aligned after recent edits?
- Finding IDs in debate-index.md → exist in the correct topic's
  findings-under-review.md (not assigned to wrong topic)?
- Convergence note cross-references in sub-topic findings → target section
  exists in 000-framework-proposal/findings-under-review.md?
- x37 references (x38_RULES.md §7) → files exist on disk?
  (Note: x37 content INTERPRETATION cannot be verified within x38 scope.
  Flag critical interpretation-dependent claims as [UNVERIFIABLE-WITHIN-X38].)

Report format — group by severity:
  [BLOCK-DEBATE] Prevents valid debate from continuing
  [BLOCK-DRAFT]  Prevents drafting specs from closed topics
  [BLOCK-PUBLISH] Prevents publishing specs
  [WARNING]      Should fix, not blocking
  [NOTE]         Low priority observation

If applicable, add separate meta-audit sections after governance findings:
  - Resolved Meta-Issues
  - Open Interpretive Disagreements
  - Methodological Limitations

For any cohort-wide or blocker finding, state:
  - denominator
  - known exceptions
  - whether the blocking trigger has already fired

End with:
  - Sync table: exact files that need syncing (with what they should say)
  - System health: blocking counts, drift hotspots, wave readiness
  - Coverage note: what you deliberately did NOT verify and why
```

---

## Mode: Quick Audit

When: daily check, after a debate round, quick status verification.
Single-agent (Chat or Agent read-only) is sufficient.

```
Role: Codex (governance auditor)
Scope: Quick audit of {FOCUS_PATHS}
Output: Report only — do not modify x38 governance source files.

After loading context:

1. STATUS DRIFT: For topics in {FOCUS_PATHS}, compare authoritative source
   (final-resolution.md or findings-under-review.md) against README.md,
   debate-index.md, and EXECUTION_PLAN.md. Check topic status matches
   actual artifact state (OPEN/DEBATING/CLOSED/SPLIT).

2. LATEST ARTIFACT: Is the most recent round file consistent with
   findings-under-review.md status table?

3. CROSS-REFERENCES: Do files in {FOCUS_PATHS} reference other files
   correctly? Convergence note refs (C-*) resolve? Finding IDs (F-*)
   assigned to correct topic? Any broken pointers?

4. WAVE CONSISTENCY: Is the topic's wave assignment in debate-index.md
   consistent with its dependencies and current state?

5. If a finding appears cohort-wide, structural, or blocker-level, do not stop
   at local examples. Escalate to denominator/exception verification or to a
   full audit before publishing final scope/severity.

Report: [BLOCK-DEBATE] / [WARNING] / [NOTE] only for {FOCUS_PATHS}.
Keep report under 50 lines.
```

---

## Mode: Maintenance (After Updates)

When: after committing changes, to catch cascade effects.
Single-agent usually sufficient. Subagents only for wide diffs (10+ files).

```
Role: Codex (governance auditor)
Scope: Maintenance audit on recent changes
Diff range: {DIFF_RANGE} (default: HEAD~5..HEAD)
Output: Report only — do not modify x38 governance source files.

1. Identify changed files:
   git diff {DIFF_RANGE} --name-only

2. For each changed file:
   a. If in docs/: change contradicts topic-dir findings or design_brief.md?
   b. If under debate/<topic-dir>/: change conflicts with other rounds,
      findings-under-review.md, or final-resolution.md?
   c. If root governance doc (AGENTS.md, x38_RULES.md, PLAN.md,
      EXECUTION_PLAN.md): change breaks cross-references?
   d. If prompt template or wrapper changed: is canonical workflow still aligned
      across debate/prompt_template.md and template/prompte/?
   e. Terminology still consistent after the change?
   f. If topic split or restructured: finding IDs (F-*) reassigned correctly?
      Convergence note refs updated in affected sub-topics?
      debate-index.md totals recalculated?

3. Cascade check: which OTHER files need updating as a consequence?

4. If a changed file creates a cohort-wide compliance issue or possible
   `[BLOCK-*]` condition, verify denominator, exceptions, and trigger state
   before publishing final severity.

Report:
  - Safe changes (no cascade needed)
  - Problematic changes (with [BLOCK-*] / [WARNING] severity)
  - Files that need syncing as a consequence
  - Whether debate-index.md needs updating (totals, wave assignments, finding counts)
```

---

## Anti-Patterns (excluded from this rewrite)

| What was removed | Why |
|---|---|
| "List every file recursively with line counts" | Wastes context. Codex IDE has repo access. |
| `__init__.py` existence check | File does not exist in x38. |
| `tmp/` or `audits/` as governance truth | `tmp/` holds working prompt copies; `audits/` holds persistent audit reports. Neither is authority on x38 repository state. |
| Assume 000 is an active debate topic | 000 is SPLIT (2026-03-22). It holds convergence notes (C-01→C-12) only. |
| Assume only topics 000-006 exist | Topic set evolves. Read debate-index.md dynamically; do not hardcode topic totals or ranges from this template. |
| Hardcode dependency map | Dependencies evolve. Always read debate-index.md §Dependencies dynamically. |
| `Python Path: .venv` | x38 is blueprint-only (AGENTS.md line 4). |
| `[CRITICAL] must fix before implementation begins` | x38 stops at blueprint. Use [BLOCK-DEBATE/DRAFT/PUBLISH]. |
| `depth 4 × threads 8` | Not a standard Codex IDE control surface. |
| `debate/004-meta-knowledge/debate-index.md` | Wrong path. Correct: `debate/debate-index.md`. |
| 6 mandatory agents for every review | Single-agent default. Subagents opt-in for full audit only. |
| Confidence scores (1-10) | Subjective. Use severity levels with actionable items instead. |
| Verify x37 interpretation correctness | Outside audit scope. Flag as [UNVERIFIABLE-WITHIN-X38]. |
