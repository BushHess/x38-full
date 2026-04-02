# 04 — Governance Simplification

> Solves: D-01, D-02, D-03, D-04, D-05
> Status: DRAFT

---

## Problem Summary

- 6 files must be manually synced per closure — persistent drift (D-01)
- Per-topic cross-topic tensions tables create maintenance burden (D-02)
- 4-tier authority hierarchy adds cognitive load for every agent (D-03)
- `[extra-archive]` rule unenforced (D-04)
- design_brief.md frozen as stale historical snapshot (D-05)

---

## Solution 1: Single Authoritative Ledger (kills D-01, D-02)

### Principle
ONE file is the source of truth for project status. Everything else is derived or informational.

### Design

**Authoritative** (must be accurate):
```
decisions/             ← Domain files ARE the decisions (self-contained)
00-status.md   ← Deferred items, circular deps, integration log
```

**Informational** (may lag, explicitly marked):
```
PLAN.md                ← Project narrative. Add header: "Status may lag. Check decisions/ for current state."
```

**Removed**:
```
EXECUTION_PLAN.md      ← ARCHIVE (move to archive/). Replaced by decisions/ + 00-status.md
debate-index.md        ← ARCHIVE. Was topic registry; replaced by domain file headers
```

### What changes per closure

OLD (6 updates):
1. Topic final-resolution.md
2. debate-index.md
3. PLAN.md
4. EXECUTION_PLAN.md
5. architecture_spec.md stub
6. Downstream findings-under-review.md cross-topic tensions

NEW (3-4 updates):
1. Domain file: move finding from `## Open` to `## Decided`
2. Downstream domain files: add `## Constraints` entry (closure workflow Step 2)
3. `00-status.md`: update Domain Status table + Integration Log
4. (If applicable) Update Deferred Items Registry or Circular Dependencies

> **AUDIT NOTE (2026-03-29)**: Original plan claimed "2 updates". Honest count
> is 3-4. Still a significant improvement over 6, but not as clean as claimed.
> The key improvement is that updates 1-2 are SUBSTANTIVE (actual decisions)
> while 3-4 are STATUS TRACKING (mechanical table updates). Old system had
> 6 updates where most were redundant status syncs across overlapping files.

### Per-topic tensions tables (D-02)

**Eliminated**. Cross-domain relationships are expressed through:
- `depends_on` / `blocks` in domain file headers
- `## Constraints` sections (imported decisions)
- `00-status.md` for deferred/circular items

No redundant per-domain tension tables to maintain.

---

## Solution 2: 2-Tier Authority (kills D-03)

### Current: 4 tiers
```
Tier 1: published/
Tier 2: debate/NNN-slug/
Tier 3: docs/design_brief.md
Tier 4: PLAN.md
```

### New: 2 tiers

| Tier | Contains | Rule |
|------|----------|------|
| **Decisions** | `decisions/*.md` (DECIDED findings), `published/*.md` (final specs) | Authoritative. If it says X, X is true. |
| **Context** | `PLAN.md`, `docs/`, `archive/` | Informational. May be outdated. Check Decisions tier if unsure. |

### Rules
1. Agents MUST read relevant domain files before writing.
2. Agents MAY read PLAN.md and docs/ for background.
3. If conflict between tiers: Decisions wins. Always.
4. design_brief.md moves to Context tier (see D-05 below).

---

## Solution 3: Evidence Rules Cleanup (kills D-04, D-05)

### `[extra-archive]` rule (D-04)

**Decision**: DROP the labeling rule. Replace with:
- All evidence used in a finding MUST be either:
  - (a) Contained within `x38/` tree (inline quote or file reference), OR
  - (b) Frozen copy placed in `x38/docs/evidence/` with retrieval date
- No labeling convention. Either it's in-tree or it's not allowed.

### design_brief.md (D-05)

**Decision**: Reclassify as historical input.
- Move to `x38/docs/design_brief.md` (stays where it is)
- Add header: `> Historical input document (2026-03-XX). For current decisions, see decisions/. This file is NOT maintained post-debate.`
- Remove Tier 3 authority claim
- Agents treat it as background reading, not binding

---

## New Agent Onboarding (simplified)

### OLD reading order (6 docs):
1. docs/online_vs_offline.md
2. x38_RULES.md
3. PLAN.md
4. docs/design_brief.md
5. EXECUTION_PLAN.md
6. debate/rules.md

### NEW reading order (3 docs):
1. `PLAN.md` — project narrative + onboarding context
2. `docs/online_vs_offline.md` — foundational distinction
3. Relevant `decisions/*.md` files — actual decisions to respect

Core rules embedded in PLAN.md (no separate rules files needed for rebuild structure).

> **UPDATE (2026-04-02)**: Topic 019 (18 findings: 14 gaps + 4 judgment calls)
> is the largest open topic. Its findings will use BOTH decision paths per Solution 4.
> discovery_spec.md already at DRAFTING (§6-§11 proposals from 019, non-authoritative).
> methodology_spec.md also added to drafts/README (from 013 closure).

---

## Solution 4: Decision Process for Open Findings

### Principle
The rebuild reorganizes findings and governance but does not change HOW
decisions are made. Open findings still require debate or deliberation.

### Two decision paths

| Path | When | Process | Output |
|------|------|---------|--------|
| **Structured debate** | Contentious findings with 2+ defensible positions | Multi-round canonical debate between the participants declared for that domain. Same rules as old x38 debates: steel-man, evidence hierarchy, max rounds | CONVERGED or ARBITRATED |
| **Direct authoring** | Spec-tightening, conventional defaults, or findings where human already has clear direction | Human researcher writes decision directly with rationale | AUTHORED or DEFAULT |

### Rules

1. Findings classified as "Judgment call" in findings-under-review.md → Structured debate
2. Findings classified as "Thiếu sót" (missing) → Either path, human researcher chooses
3. If structured debate reaches max rounds without convergence → Human ARBITRATES
4. All decisions documented in domain file `## Decided` with type tag

### Debate rules (simplified from old debate/rules.md)

Retained from old system:
- Evidence hierarchy: formal proof > statistical test > empirical observation
- Steel-man requirement: each side must state opponent's best argument
- Max 6 rounds per finding before escalation to human
- Judgment calls decided by human researcher (Tier 3 authority)

Removed from old system:
- Per-topic cross-tensions tables (replaced by domain constraints)
- `[extra-archive]` labeling (replaced by in-tree-or-frozen)
- Wave/tier scheduling (replaced by depends_on DAG)

---

## Solution 5: Live Debate Surface + External AI Inputs

### Principle
Rebuild MUST keep a live debate workspace for remaining open domains. `decisions/`
stores authoritative state; `debate/` stores round artifacts, counterarguments,
and external advisory inputs. Without this split, open findings have nowhere to
be argued after old topic directories are archived.

### Live structure

```text
x38/
├── decisions/                  ← authoritative domain state
├── debate/                     ← LIVE debate workspace for remaining open domains
│   ├── 03-identity-versioning/
│   │   ├── README.md           ← canonical participants, current round, issue scope
│   │   ├── rounds/
│   │   │   ├── claude_code/round-1.md
│   │   │   └── codex/round-1.md
│   │   └── external/
│   │       └── chatgpt_web/2026-04-02-round-1.md
│   └── 17-epistemic-search/
│       └── ...
└── archive/
    └── debate/                 ← old topic-based x38 debates (read-only)
```

### Canonical vs advisory participants

| Role | Writes where | Authority |
|------|--------------|-----------|
| **Canonical participants** | `debate/{domain}/rounds/{participant}/...` | Can directly move findings toward CONVERGED / ARBITRATED |
| **External advisors** | `debate/{domain}/external/{source}/...` | Evidence/advisory only. Never authoritative by themselves |
| **Human researcher** | `decisions/*.md`, judgment notes | Final arbiter for ARBITRATED / AUTHORED / DEFAULT decisions |

### Rule for ChatGPT web

`chatgpt_web` is treated as an **external advisor**, not a canonical debater, unless
the project explicitly upgrades to an N-participant governance model. This keeps
the rebuild compatible with the current x38 debate logic while still allowing
ChatGPT to contribute real critique.

### Required metadata for external AI artifacts

Every file under `debate/{domain}/external/chatgpt_web/` MUST include:
- `source: chatgpt_web`
- `captured_at_utc`
- `operator`
- `prompt_source`
- `repo_snapshot`
- `context_files`
- `model_label_if_shown`
- `browsing_used: yes/no/unknown`
- Raw response body
- Normalized claims / issue mapping

### Admissibility rule

An external AI claim becomes binding ONLY when one of:
1. A canonical participant adopts it in a round artifact with evidence.
2. A canonical participant rebuts it and records why it fails.
3. Human researcher cites it in an ARBITRATED / AUTHORED decision.

This prevents ChatGPT-web transcripts from silently becoming canonical state.

### If you want ChatGPT as a true third debater

That is allowed only with an explicit governance upgrade:
- Domain README declares `canonical_participants: [claude_code, codex, chatgpt_web]`
- Round parity / closure rules apply to ALL canonical participants
- `final-resolution.md` records any asymmetry or missing final response

Default recommendation: do NOT do this for rebuild v1. Use ChatGPT web as an
external advisory lane first; upgrade later only if the extra process cost is justified.

---

## Verify Checklist

- [ ] EXECUTION_PLAN.md archived (not deleted — moved to archive/)
- [ ] debate-index.md archived
- [ ] PLAN.md has "informational, may lag" header
- [ ] design_brief.md has "historical input" header
- [ ] Per-closure update reduced to 3-4 files (2 substantive + 1-2 status tracking)
- [ ] No per-domain tensions tables exist
- [ ] 2-tier authority documented in PLAN.md
- [ ] `[extra-archive]` rule replaced with in-tree-or-frozen policy
- [ ] Agent onboarding path reduced to 3 docs
- [ ] debate/rules.md governance rules consolidated into PLAN.md or decisions/ headers
- [ ] Live `debate/` tree retained for open domains after rebuild
- [ ] `chatgpt_web` external-advisor lane defined under `debate/{domain}/external/`
