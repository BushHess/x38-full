# 08 — N-Participant Debate Protocol

> Solves: ChatGPT Pro integration as canonical debater, N-participant generalization
> Status: CONVERGED (debate converged at C.3, closure note C.4; 12/12 items, 0 open)
> Evidence: `tmp/trilateral_debate_protocol.md` (debate artifact, read-only)
> Participants: claude_code, chatgpt_pro (bilateral debate, 3 rebuttal rounds + closure note)
> Constitutional note: Codex did not participate in this debate. This file is a
> rebuild proposal, not a formal x38 decision. Requires human ratification or
> Codex sanity-check before becoming binding governance.
> Scope: v1 covers 2 or 3 canonical participants. Rules are written N-generic
> where possible, but orchestration workflow is tested for N ≤ 3.

---

## Problem Summary

- `x38_RULES.md` §5 hard-codes 2 participants (claude_code + codex)
- `debate/rules.md` steel-man, convergence, round parity designed for bilateral only
- `debate/prompt_template.md` hard-codes "Claude Code ↔ Codex"
- ChatGPT Pro limited to external advisory lane (`04-governance.md` Solution 5)
- No mechanism for human researcher to opt-in a third canonical participant
- Topic 018 precedent: 4-agent session ruled extra-canonical under current rules

---

## 6 Converged Decisions

### D1. Opt-in Canonical Participant Model

**Default**: `canonical_participants: [claude_code, codex]` (bilateral baseline).

**Opt-in**: Human researcher adds `chatgpt_pro` (or any available participant)
to `canonical_participants` in domain/topic README when:
- Finding is Judgment call with 2+ defensible positions
- Topic needs fresh perspective (blind spots, cross-domain)
- Human researcher judges the 3-party process cost is worthwhile

**Advisory fallback**: Agent not opted-in as canonical can still contribute
via `external/` lane per admissibility rule (04-governance.md Solution 5).

**Available pool** (declared in §5):

| Agent | Role | Strength |
|-------|------|----------|
| `claude_code` | Architect + opening critic | Deep btc-spot-dev knowledge |
| `codex` | Reviewer + adversarial critic | Fresh perspective |
| `chatgpt_pro` | Reviewer + independent critic | Different model bias; blind spot detection |

### D2. Single-Writer Invariant

Only ONE writer commits debate artifacts to repo:
- **Default**: Human orchestrator (copy artifact from agent session → repo).
- **Alternative**: MCP/orchestrator service (automation option, not required).
- Agents NEVER commit directly to canonical files.

Purpose: avoid merge conflicts, serialize writes, ensure provenance.

### D3. Max Rounds Formula

```
max_rounds_per_finding = 3 × len(canonical_participants)
```

| Canonical count | Max rounds | Exchange cycles |
|----------------|-----------|----------------|
| 2 | 6 | 3 per agent |
| 3 | 9 | 3 per agent |

This is a **ceiling**, not a target — close early when converged.

### D4. Parallel Round 1 (for N ≥ 3)

When `len(canonical_participants) ≥ 3`:
- **Round 1**: Architect writes opening. Remaining reviewers write
  rebuttals **independently, without seeing each other's artifacts**.
  Human orchestrator ensures isolation.
- **Round 2+**: Round-robin on full history.

When `len(canonical_participants) = 2`: bilateral flow unchanged.

Human override: if parallel R1 not feasible for operational reasons,
note the exception in README or round packet.

### D5. Generalized Convergence Rules (§26)

**Protocol layer** (when to escalate):

- `Converged` = ALL canonical participants unanimous + steel-man
  obligations completed per §7(d).
- `Non-unanimous` after `max_rounds_per_finding` → auto-escalate
  to `Judgment call`. Dissent record required:
  - Dissenting position (who, specific argument)
  - Supporting evidence
  - Majority rationale (if majority exists)
  - Dissenting agent MUST steel-man majority position before recording dissent
- `majority-dissent` and `split` are **debate-status markers**,
  not final decision type tags.

**Decision type layer** (how to tag closure):

Human researcher applies rebuild taxonomy: CONVERGED, ARBITRATED,
AUTHORED, DEFAULT, DEFERRED. Taxonomy is the decision layer;
§26 is the protocol layer. They complement, not replace, each other.

**Closure gate** (§14c): A finding CANNOT be closed unless every canonical
participant has either (a) responded in the current/final round, or
(b) provided explicit waiver recorded in `final-resolution.md`.
"Closing quickly" when a participant hasn't responded the final round
is a governance violation, not an efficiency gain.

**Round parity** (§14b): Before closure or Judgment call, all canonical
participants must have total round count within ±1, OR the asymmetry
must be noted with reason in `final-resolution.md`.
Exception: Parallel R1 (reviewers write same round-1 while architect
only has round-1 opening) — asymmetry by design, no note required.

**Scope**: §26 activates fully when N > 2. When N = 2, existing
bilateral rules (§7a-c, §13 max 6, §14b 2-party parity) apply.

### D6. Actor Identity + Provenance Metadata

**Actor identity** (standardized across 04-governance.md and 08):

| Field | Meaning | Examples |
|-------|---------|---------|
| `participant_id` | Canonical identity in debate | `claude_code`, `codex`, `chatgpt_pro` |
| `surface` | Interface/tool used to generate artifact | `cli`, `web`, `agent`, `project`, `api` |

Note: `04-governance.md` uses `chatgpt_web` which conflates participant and surface.
Rebuild standardizes: `chatgpt_pro` = participant_id, `web` = surface.

**Provenance metadata** — every round artifact from a participant WITHOUT
direct file-system access MUST include:

```yaml
participant_id: chatgpt_pro       # canonical identity
surface: web                      # how artifact was generated
model_label_if_shown: ...         # model name if visible in UI
browsing_used: yes/no/unknown     # web browsing during generation
captured_at_utc: ...              # timestamp
operator: ...                     # human who ran the session
prompt_source: ...                # what was pasted
repo_snapshot: ...                # commit hash or timestamp
context_files: [...]              # files included in prompt
```

This schema is a **superset** of 04-governance.md's advisory metadata.
When a participant is canonical, provenance is no less rigorous than advisory.

Role: **provenance record** (canonical) or **admissibility evidence** (advisory).

---

## Steel-Man Extension (§7d)

When N > 2 canonical participants: before marking convergence,
agent must steel-man **every distinct remaining position**.
If other agents hold K different positions, must steel-man all K.
Each position holder confirms the steel-man is fair.
Max 2 attempts per position; if rejected twice → `Judgment call`
with note `steel-man impasse (N-way)`.

When N = 2: existing §7(a)(b)(c) applies unchanged.

---

## Orchestration Workflow

```
Step 0 — Determine participants:
  Read domain/topic README → canonical_participants list.
  N = len(canonical_participants). max_rounds = 3 × N.

Step 1 — Opening:
  Human → Architect agent: paste Prompt A
  Architect writes: rounds/{architect}/round-1_opening-critique.md
  Human saves artifact to repo (§25b: human = single writer)

Step 2 — Round 1 rebuttal:
  IF N ≥ 3 (parallel):
    For EACH non-architect participant:
      Human → Reviewer: Prompt B1 (WITHOUT other reviewers' artifacts)
    (all concurrent — do not wait for each other)
    Human saves all artifacts
  IF N = 2 (bilateral):
    Human → Reviewer: Prompt B + opening critique
    Human saves artifact

Step 3 — Round-robin (Round 2+):
  Order: per canonical_participants list in README
  Each turn: Human pastes Prompt B-next + ALL existing round files
  Agent reads all, writes rebuttal/response
  Human saves artifact

Step 4 — Convergence check after each round:
  ALL issues Converged (unanimous) or Judgment call → Step 5
  Still Open → continue round-robin
  Reached max_rounds → all Open → Judgment call + dissent record

Step 5 — Closure:
  Human → any agent: Prompt C
  Agent creates/syncs final-resolution.md (decision type tags per taxonomy)
  Human reviews, decides Judgment calls, updates state
```

---

## Directory Structure

Aligned with `04-governance.md` Solution 5 live structure:

```text
debate/{domain}/
  ├── README.md                                ← declares canonical_participants
  ├── findings-under-review.md
  ├── final-resolution.md
  ├── rounds/
  │   └── {participant}/round-N_*.md           ← 1 dir per canonical participant
  └── external/
      └── {source}/*.md                        ← advisory lane (optional)
```

Participant directories under `rounds/` created only when debate starts.
Topics CLOSED before protocol upgrade keep their original structure.
Note: current x38 uses `{topic}/{participant}/` without `rounds/` layer.
Rebuild migrates to `rounds/{participant}/` per 04-governance.md.

---

## Prompt Templates

All prompts read `{canonical_participants}` from domain/topic README.
No hard-coded agent names in templates.

- **Prompt A** (Opening): `Các bên tranh luận: {participants joined by " ↔ "}`
- **Prompt B1/B2** (Parallel R1, N ≥ 3 only): independent rebuttal, isolation enforced
- **Prompt B-next** (Round-robin R2+): reads ALL round files from ALL participants
- **Prompt C** (Closure): `Participants: {canonical_participants}`

When N = 2: skip B1/B2, use existing bilateral Prompt B.

---

## Status Table Format

Dynamic columns per canonical participants:

```markdown
| Issue ID | Point | Class | Status | CC | CX | GP | Steel-man | Rejection reason |
```

When N = 2 (default): drop GP column.

Abbreviations per §5: CC = claude_code, CX = codex, GP = chatgpt_pro.

---

## Final Resolution Template

```markdown
**Participants**: {canonical_participants}

| Issue ID | Finding | Resolution | Decision type | Round closed | Dissent |
|----------|---------|------------|--------------|-------------|---------|

## Dissent records

### {Issue ID} — {name}

**Majority position** ({agents}): [position]
**Dissent** ({agent}): [position]
**Dissent evidence**: [pointers]
**Majority rationale**: [why dissent doesn't hold]
**Human decision**: [choose majority / dissent / synthesize / defer]
**Decision type**: ARBITRATED
```

---

## Impact on Other Rebuild Files

**Rule precedence**: Until the updates below are merged, 08 supersedes
debate-related content in 04/02/01/07 where they conflict. Specifically:
- 04-governance.md Solution 5 "do NOT do this for v1" → overridden by D1
- 04-governance.md "max 6 rounds" → overridden by D3 formula
- 04-governance.md `chatgpt_web` identity → overridden by D6 `chatgpt_pro`
- 04-governance.md `rounds/{participant}/` directory → **retained** (08 aligned to 04)

| File | Required update |
|------|----------------|
| `04-governance.md` Solution 5 | Replace "default: do NOT do this for v1" with D1 opt-in model |
| `04-governance.md` Solution 4 | Embed §25b, §26, formula §13 in debate rules section |
| `04-governance.md` Solution 5 | Standardize actor ID: `chatgpt_pro` + `surface` field per D6 |
| `02-concept-structure.md` | Domain file template includes `canonical_participants` field |
| `01-taxonomy.md` | Note: taxonomy = decision type layer; §26 = protocol layer |
| `07-genesis-pipeline.md` | Migration step includes trilateral protocol adoption |

---

## Verify Checklist

- [ ] §5 lists 3 available participants with opt-in note
- [ ] `canonical_participants` field in domain/topic README template
- [ ] Default is `[claude_code, codex]` (bilateral)
- [ ] §25b single-writer invariant written as explicit rule
- [ ] §13 uses formula `3 × len(canonical_participants)`
- [ ] §7(d) generalized for N > 2 steel-man
- [ ] §26 convergence rules are canonical-participants-aware
- [ ] §14b round parity rule (±1 round count or noted asymmetry)
- [ ] §14c closure gate (all canonical responded or explicit waiver)
- [ ] Prompt templates use `{canonical_participants}`, no hard-coded names
- [ ] Parallel B1/B2 only when N ≥ 3
- [ ] Directory structure dynamic per canonical_participants + external/ lane
- [ ] Status table columns adapt to participant count
- [ ] Final resolution template includes Dissent column + Decision type tags
- [ ] Metadata block required for non-CLI participant artifacts
- [ ] `04-governance.md` Solution 5 updated (opt-in replaces advisory-only default)
- [ ] Topics CLOSED before upgrade keep bilateral structure unchanged
