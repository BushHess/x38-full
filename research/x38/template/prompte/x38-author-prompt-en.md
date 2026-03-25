# x38 Claude Code Debate Author — Format Supplement

Format-only supplement for Claude Code (architect / opening critic).
**All substance lives in canonical sources** — this file adds ONLY output format,
variables, and anti-patterns.

**Canonical sources (read these for rules, not this file):**

| What | Where |
|---|---|
| Debate rules (steel-man, evidence, convergence, context loading §25) | `debate/rules.md` |
| Round format + closure steps (Prompt A/B/C + Template D) | `debate/prompt_template.md` |
| Framework rules (authority, participants, scope) | `x38_RULES.md` |

---

## Variables

| Variable | Required | Description | Example |
|---|---|---|---|
| `{MODE}` | yes | `opening`, `reply`, or `closure` | `reply` |
| `{TOPIC_DIR}` | yes | Topic directory name | `007-philosophy-mission` |
| `{ROUND_NUM}` | yes | Current round number | `2` |
| `{MESSAGE_TYPE}` | Mode A/B | `opening-critique`, `author-reply`, or `final-status` | `author-reply` |
| `{ISSUE_SCOPE}` | yes | Stage or issue subset being debated / closed | `Stage 1: PM-01→PM-05` |
| `{INPUT_ARTIFACT}` | Mode B | Path to Codex's artifact | `debate/007-.../codex/round-1_rebuttal.md` |
| `{OUTPUT_PATH}` | Mode A/B | Where to save the round artifact | `debate/007-.../claude_code/round-2_author-reply.md` |
| `{PRECEDENT_PATH}` | optional | Completed debate for reference | `debate/004-meta-knowledge/` |

---

## Mode A — Opening Critique (format only)

Precedent: `debate/004-meta-knowledge/claude_code/round-1_opening-critique.md`

Substance: follow `debate/prompt_template.md` Prompt A + `rules.md` §25.

```
Role: Claude Code (architect / opening critic)
Mode: opening | Round: {ROUND_NUM} | Scope: {ISSUE_SCOPE}
Output: {OUTPUT_PATH}

HEADER (mandatory):
  # Round {ROUND_NUM} — Opening Critique: {Topic Name}
  **Topic**: {TOPIC_DIR full name}
  **Author**: claude_code
  **Date**: YYYY-MM-DD
  **Scope**: {ISSUE_SCOPE}
  **Input documents**: (list all files read)

PREAMBLE (2-4 paragraphs):
  - Establish architect role
  - State burden of proof (→ rules.md §5)
  - Critical context + scope boundaries

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

Precedent: `debate/004-meta-knowledge/claude_code/round-2_author-reply.md`

Substance: follow `debate/prompt_template.md` Prompt B + `rules.md` §7-§8.
This section adds the Part A/B split structure.

```
Role: Claude Code (architect / author)
Mode: reply | Round: {ROUND_NUM} | Scope: {ISSUE_SCOPE}
Input: {INPUT_ARTIFACT} | Output: {OUTPUT_PATH}

HEADER: same as Mode A, titled "Author Reply".

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

## Mode C — Closure

Follow `debate/prompt_template.md` Prompt C + Template D. No additional format
needed — Prompt C now contains prerequisites, 5-step process, and verify step.

Precedent: `debate/004-meta-knowledge/final-resolution.md` + `judgment-call-deliberation.md`

---

## Usage Workflow

```
1. Human decides mode, fills in variables.
2. Paste the appropriate Mode (A, B, or C) as the prompt.
3. Mode A/B: Claude Code writes artifact to {OUTPUT_PATH}.
   Mode C: Claude Code updates closure artifacts per Prompt C steps.
4. Human reviews → passes to Codex (debate continues) or runs Mode C (closing).
```

---

## Per-Issue Format Quick Reference

From Topic 004 (not invented):

```markdown
## MK-01: Maturity Pipeline — ACCEPT observation, REJECT mechanism

### Position
[Analysis with inline evidence]
**Key argument**: [one sentence]
Evidence: `RESEARCH_PROMPT_V8.md` lines 635-644
**However**, [self-challenge]...
**Proposed design principle**: [concrete amendment]

### Classification: Thiếu sót
[1-2 sentence rationale]
```

---

## Anti-Patterns

| Excluded | Why |
|---|---|
| Generic "counter-argument" framing | Claude Code is architect, not generic reviewer |
| Confidence tags `[high] [medium] [speculative]` | Not canonical. Use classification + status table |
| Free-form "OPEN QUESTIONS" section | Scope drift. Unresolved → Open or Judgment call |
| "Scan ALL other files in x38" | Context waste. Read evidence for `{ISSUE_SCOPE}` only |
| Python code | x38 = blueprint only (AGENTS.md) |
| Hardcoded output paths | Use `{OUTPUT_PATH}` / Mode C known files |
| Non-canonical `{MESSAGE_TYPE}` values | Align with `debate/rules.md` naming |
| "Check debate-index.md for previous rounds" | It indexes topics, not rounds |
