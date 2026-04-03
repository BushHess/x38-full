# 06 — Single-Source Tracking

> Solves: F-01, F-02, F-03
> Status: DRAFT

---

## Problem Summary

- PLAN.md vs EXECUTION_PLAN.md vs debate-index.md diverge on topic counts and status (F-01)
- Topics 003/006 not synced with Topic 018 routing obligations (F-02)
- Deferred items scattered across individual final-resolution.md files, no global view (F-03)

---

## Solution: Single Ledger in 00-status.md

### Principle
ONE file tracks all dynamic state. Domain decision files track static state (decided findings). The only file that changes frequently is `00-status.md`.

### Structure of 00-status.md

```markdown
# Project Status & Open Questions

> This is a TRACKING FILE, not a concept domain.
> It lives in decisions/ for convenience but does NOT contain findings.
> Authoritative for: project status, deferred items, circular deps, integration log, spec readiness, export readiness.

## Domain Status

> [TEMPLATE — populate with real counts during rebuild Step 0 extraction]

| Domain | Decided | Open | Deferred | Constraints | Status |
|--------|---------|------|----------|-------------|--------|
| 01-philosophy | ? | 0 | 0 | 0 | INTEGRATED |
| 02-campaign-model | ? | 0 | 0 | 0 | INTEGRATED |
| 03-identity-versioning | ? | ? | 0 | ? | ACTIVE |
| 04-firewall | ? | 0 | 0 | 0 | INTEGRATED |
| 05-meta-knowledge | ? | 0 | 0 | 0 | INTEGRATED |
| 06-clean-oos | ? | 0 | 0 | 0 | INTEGRATED |
| 07-convergence | ? | 0 | ? | 0 | DECIDED (deferred items) |
| 08-search-expansion | ? | 0 | 0 | 0 | INTEGRATED |
| 10-protocol-engine | 0 | 3 | 0 | 1 | BLOCKED (F-05, F-36, F-37 Open + SSE-D-04 Constraint from 018; waits 03-identity, 16, 17A, 18A, 18D1) |
| 11-engine-design | 0 | 4 | 0 | 0 | ACTIVE (F-07 + ER-01/02/03) |
| 12-feature-engine | 0 | 2 | 0 | 1 | ACTIVE (F-08, F-38 Open + SSE-D-03 Constraint from 018) |
| 13-data-integrity | 0 | 2 | 0 | 0 | ACTIVE |
| 14-deployment | 0 | 2 | 0 | 0 | ACTIVE |
| 15-quality-assurance | 0 | 2 | 0 | 0 | ACTIVE (F-18, F-39; F-19 demoted) |
| 16-bounded-recalibration | 0 | 2 | 0 | 0 | BLOCKED (BR-01, BR-02; waits 03-identity, 14-deployment) |
| 17-epistemic-search | — | — | — | — | **SPLIT** (2026-04-03) → 17A + 17B below |
| 17A-intra-campaign-esp | 0 | 2 | 0 | 1 | ACTIVE (ESP-01, ESP-04 + SSE-04-CELL; all deps satisfied) |
| 17B-inter-campaign-esp | 0 | 2 | 0 | 1 | BLOCKED (ESP-02, ESP-03 + SSE-08-CON; waits 17A) |
| 18-discovery-feedback-loop | — | — | — | — | **SPLIT** (2026-04-02) → 9 sub-domains below |
| 18A-discovery-foundations | 0 | 3 | 0 | 0 | ACTIVE (DFL-04,05,09; Tier 1 — debate FIRST) |
| 18B-ai-analysis-reporting | 0 | 3 | 0 | 0 | BLOCKED (DFL-01,02,03; waits 18A) |
| 18C-systematic-data-exploration | 0 | 2 | 0 | 0 | BLOCKED (DFL-06,07; waits 18A, parallel with 18B) |
| 18D-discovery-governance | — | — | — | — | **SPLIT** (2026-04-02) → 3 sub-domains below |
| 18D1-pipeline-structure | 0 | 2 | 0 | 0 | BLOCKED (DFL-08,10; waits 18A+B, parallel with 18D2) |
| 18D2-statistical-budget | 0 | 1 | 0 | 0 | BLOCKED (DFL-11; waits 18A+B, parallel with 18D1) |
| 18D3-grammar-expansion | 0 | 1 | 0 | 0 | BLOCKED (DFL-12; waits 18D2) |
| 18E-data-quality-validation | 0 | 2 | 0 | 0 | ACTIVE (DFL-13,17; independent) — regrouped from 3→2 |
| 18F-regime-dynamics | 0 | 2 | 0 | 0 | ACTIVE (DFL-14,18; independent) — DFL-14 moved from 18E, tension resolution |
| 18G-data-scope | 0 | 2 | 0 | 0 | ACTIVE (DFL-15,16; independent) — new, split from 18F |

## Deferred Items Registry

| ID | Decision deferred | Blocked by | Unblocks | Provisional value |
|----|-------------------|------------|----------|-------------------|
| X38-CVG-THR | Convergence numeric floors | 17A-intra-campaign-esp | architecture §9.3 | methodology frozen, numerics TBD |
| X38-CVG-THR-3a | Robustness minimum numerics | 17A-intra-campaign-esp | architecture §9.4 | owned by convergence domain |
| ... | ... | ... | ... | ... |

## Circular Dependencies

| Pair | Interface | Resolution | Status |
|------|-----------|------------|--------|
| 07-convergence <-> 17A-intra-campaign-esp | metric methodology ↔ consumption criteria | PENDING | Cannot freeze until 17A has DECIDED findings. See 03-dependency-rules.md. 017 SPLIT (2026-04-03): circular dep is with 017A only (v1, consumption framework). 017B (v2, inter-campaign) not involved. |
| ... | ... | ... | ... |

## Integration Log

> [TEMPLATE — backfill from rebuild date forward, not from old topic closure dates.
>  Old closures happened before domains existed. Integration log starts when
>  rebuild is executed and new domain files are created.]

| Date | Domain closed | Downstream updates | Verified by |
|------|--------------|-------------------|-------------|
| (rebuild date) | Initial extraction: 8 closed-topic domains populated | All constraint sections populated | human |
| ... | ... | ... | ... |

## Spec Readiness

| Spec | Status | Stubs remaining | Blocking domains |
|------|--------|----------------|------------------|
| architecture_spec.md | DRAFTING | 4 stubs + 1 proposal | 03-identity, 13-data, 16-recal, 17A/17B-esp; §14 proposal from 18-DFL |
| meta_spec.md | SEEDED (DRAFTING-READY) | 0 (transcription only) | none |
| discovery_spec.md | DRAFTING (partial) | §1-5 authoritative, §6-11 proposals | 18A-D1/D2/D3 (§6-§11 non-authoritative until CLOSED); 18E-G independent |
| methodology_spec.md | DRAFTING | 0 | none (from 013 closure) |
| protocol_spec.md | NOT STARTED | N/A | 10-protocol-engine |
| engine_spec.md | NOT STARTED | N/A | 11-engine-design |
| feature_spec.md | NOT STARTED | N/A | 12-feature-engine |

## Export Readiness (genesis/)

> Added per 07-genesis-pipeline.md (J-01). Tracks progress toward alpha_lab/genesis/.
> A section is EXPORTABLE when: source domain INTEGRATED + content ready
> (standard: spec ≥ REVIEW; lightweight: direct assembly) + abstraction test
> PASS + no blocking DEFERRED items + genesis_target declared.

| genesis/ section | Source domain(s) | Spec status | Abstraction test | Export status |
|-----------------|------------------|-------------|------------------|--------------|
| specs/philosophy.md | 01-philosophy | PENDING | NOT_TESTED | PENDING |
| specs/campaign_model.md | 02-campaign-model | PENDING | NOT_TESTED | PENDING |
| specs/identity_versioning.md | 03-identity-versioning | PENDING | NOT_TESTED | PENDING |
| specs/firewall.md | 04-firewall | PENDING | NOT_TESTED | PENDING |
| specs/meta_knowledge.md | 05-meta-knowledge | PENDING | NOT_TESTED | PENDING |
| specs/clean_oos.md | 06-clean-oos | PENDING | NOT_TESTED | PENDING |
| specs/convergence.md | 07-convergence | PENDING | NOT_TESTED | PENDING |
| specs/search_expansion.md | 08-search-expansion | PENDING | NOT_TESTED | PENDING |
| specs/protocol_engine.md | 10-protocol-engine | PENDING | NOT_TESTED | PENDING |
| specs/engine_design.md | 11-engine-design | PENDING | NOT_TESTED | PENDING |
| specs/feature_engine.md | 12-feature-engine | PENDING | NOT_TESTED | PENDING |
| specs/data_integrity.md | 13-data-integrity | PENDING | NOT_TESTED | PENDING |
| specs/deployment.md | 14-deployment | PENDING | NOT_TESTED | PENDING |
| specs/quality_assurance.md | 15-quality-assurance | PENDING | NOT_TESTED | PENDING |
| specs/bounded_recalibration.md | 16-bounded-recalibration | PENDING | NOT_TESTED | PENDING |
| specs/epistemic_search.md | 17-epistemic-search (17A + 17B) | PENDING | NOT_TESTED | PENDING |
| specs/discovery_feedback_loop.md | 18A-D1/D2/D3 (architecture) + 18E-G (data) | PENDING | NOT_TESTED | PENDING |
| specs/entity_lifecycle.md | 03, 16 + X40 (state machines) | PENDING | NOT_TESTED | PENDING |
| README.md | ALL (assembly — written last) | N/A | NOT_TESTED | PENDING |
```

---

## How this solves each issue

### F-01 (PLAN vs EXECUTION_PLAN vs debate-index diverge)

**Before**: 3 files with overlapping status tables, manually synced, persistently drifting.
**After**: 1 file (00-status.md) has the `## Domain Status` table. PLAN.md is narrative-only with header "check decisions/ for status". EXECUTION_PLAN.md and debate-index.md archived.

### F-02 (003/006 not synced with 018 routing)

**Before**: Topic 018 closes, routing obligations scattered in its final-resolution.md. Consumer topics must self-update. 003/006 didn't.
**After**: Closure workflow (03-dependency-rules.md, Solution 3) requires explicit downstream update. Integration Log in 00-status.md tracks that update happened. If 003/006 equivalent domains don't have constraints entries, Integration Log shows gap.

### F-03 (Deferred items scattered)

**Before**: Deferred decisions buried in individual final-resolution.md. No global view.
**After**: `## Deferred Items Registry` in 00-status.md. Single table of all deferred items with blocked_by, unblocks, provisional value.

---

## Update Rules

### Who updates 00-status.md

1. **Domain Status table**: Updated by human researcher after each domain closure (Step 3 of closure workflow).
2. **Deferred Items Registry**: Updated when a finding is classified DEFERRED (at closure time).
3. **Circular Dependencies**: Updated when detected (during debate or closure).
4. **Integration Log**: Updated during Step 2 of closure workflow (downstream notification).
5. **Spec Readiness**: Updated when spec status changes (stub filled, readiness gate met).
6. **Export Readiness**: Updated when a genesis/ section advances (spec reaches REVIEW, abstraction test run, section exported). Per 07-genesis-pipeline.md.

### Frequency
- This file changes ~1-2 times per week during active debate.
- It is the ONLY frequently-changing governance file.
- All other files (PLAN.md, domain files, spec files) change less frequently.

---

## Step 0: Extraction Methodology

> **Context**: G-05 identified that extraction methodology was undefined.
> This section defines HOW findings are extracted from all topic directories
> before the rebuild can execute. Step 0 is the hard prerequisite for everything else.

### Input

All 32 directories under `debate/NNN-slug/` (19 original + 13 from splits: 017A/B, 019A-G, 019D1-D3), specifically:
- `final-resolution.md` (primary source for DECIDED findings)
- `findings-under-review.md` (primary source for OPEN/DEFERRED findings)
- Debate round files (secondary source for rationale and evidence)

### Extraction procedure (per topic)

1. **List all findings**: Extract every finding ID (F-NN, SSE-NN, BR-NN, ESP-NN, DFL-NN, ER-NN, etc.) from `final-resolution.md` and `findings-under-review.md`.
2. **Classify each finding**:
   - **Status**: DECIDED (in final-resolution with clear decision) | OPEN (in findings-under-review, no decision) | DEFERRED (explicitly deferred with blocked_by)
   - **Decision type** (per 01-taxonomy.md): CONVERGED | ARBITRATED | AUTHORED | DEFAULT | DEFERRED
   - **Reclassify JC labels**: Check each "Judgment call" — if it has a clear decision with rationale, reclassify as ARBITRATED or AUTHORED. If binary Converged, verify genuine multi-agent agreement.
3. **Assign domain**: Map finding to its target domain file (per 02-concept-structure.md mapping table). Findings that span domains go to the PRIMARY domain with a CONSTRAINT cross-reference in the secondary domain.
4. **Assign new ID**: `X38-{DOMAIN}-{NN}` per 01-taxonomy.md. Sequential within domain. Old IDs preserved in `Source:` field.
5. **Extract rationale**: 1-2 sentences summarizing WHY this position won (for DECIDED) or what the design question is (for OPEN).
6. **Assign genesis_target**: Map finding to its target section in alpha_lab/genesis/ per 07-genesis-pipeline.md domain→genesis table. Set `NONE` for process/governance findings that do not export.
7. **Evaluate 3 X40 state machine concepts**: Check 07-genesis-pipeline.md Solution 2. For each (baseline lifecycle, durability, challenger tracking): if existing finding covers it → no action. If not → create new finding in target domain.

### Output (per domain)

A draft domain file following the format in 02-concept-structure.md:
- `## Decided`: all DECIDED findings with provenance
- `## Constraints`: imported decisions from other domains
- `## Open`: all OPEN findings with positions
- `## Deferred`: all DEFERRED findings with blocked_by

### Verification pass

After all 32 topic directories are extracted:
1. **Count check**: Total extracted findings (pre-import) ≈ ~160 (known estimate). Flag if <140 or >180. After X40 import (step 7), total may increase by up to ~10 new findings — report pre-import and post-import counts separately.
2. **No orphans**: Every finding in every `final-resolution.md` and `findings-under-review.md` is accounted for.
3. **No duplicates**: No finding ID appears in two domain files (except as CONSTRAINT cross-ref).
4. **Cross-reference integrity**: Every `blocked_by` and `depends_on` reference points to a valid finding or domain.
5. **Populate 00-status.md**: Fill Domain Status table with real counts from extraction.
6. **genesis_target coverage**: Every finding has `genesis_target` assigned (or explicit `NONE`). Per 07-genesis-pipeline.md.
7. **X40 state machine audit**: 3 concepts from 07-genesis-pipeline.md Solution 2 evaluated — each either covered by existing finding or created as new finding.

---

## Final Directory Structure (complete)

```
x38/
├── PLAN.md                          ← Narrative + onboarding (informational)
├── docs/
│   ├── online_vs_offline.md         ← Foundational distinction (informational)
│   ├── design_brief.md              ← Historical input (informational)
│   └── evidence/                    ← Frozen external evidence copies
│
├── decisions/                       ← AUTHORITATIVE (17 domain files + 1 tracking file = 18 files)
│   ├── 01-philosophy.md             ┐
│   ├── 02-campaign-model.md         │ 8 consolidated domains
│   ├── 03-identity-versioning.md    │ (closed topics merged
│   ├── 04-firewall.md               │  by concept)
│   ├── 05-meta-knowledge.md         │
│   ├── 06-clean-oos.md              │
│   ├── 07-convergence.md            │
│   ├── 08-search-expansion.md       ┘
│   ├── 00-status.md                 ← TRACKING FILE (not a domain). Status, deferred, circular, log
│   ├── 10-protocol-engine.md
│   ├── 11-engine-design.md
│   ├── 12-feature-engine.md
│   ├── 13-data-integrity.md
│   ├── 14-deployment.md
│   ├── 15-quality-assurance.md
│   ├── 16-bounded-recalibration.md
│   ├── 17-epistemic-search.md       ← Topic 017 (SPLIT → 2 sub-sections: 17A intra-campaign v1, 17B inter-campaign v2; 6 findings total)
│   └── 18-discovery-feedback-loop.md ← Topic 019 (SPLIT → 9 sub-domains: 18A/B/C/D1/D2/D3/E/F/G, 18 findings total)
│
├── debate/                          ← LIVE debate workspace for remaining open domains
│   ├── 03-identity-versioning/
│   │   ├── README.md                ← canonical participants + round status
│   │   ├── rounds/
│   │   │   ├── claude_code/
│   │   │   └── codex/
│   │   └── external/
│   │       └── chatgpt_web/         ← pasted/imported ChatGPT web critiques
│   └── ... (other active domains with OPEN findings)
│
├── drafts/                          ← Spec drafts (consume decisions/)
│   ├── README.md                    ← Lifecycle rules + dependency table
│   ├── architecture_spec.md         ← DRAFTING (§14 proposal from 019)
│   ├── meta_spec.md                 ← SEEDED (transcription-ready)
│   ├── discovery_spec.md            ← DRAFTING (§1-5 auth, §6-11 proposals from 019)
│   ├── methodology_spec.md          ← DRAFTING (from 013 closure)
│   └── ... (future: protocol, engine, feature specs)
│
├── published/                       ← Final specs (read-only)
│
├── archive/                         ← OLD structure (read-only reference)
│   ├── debate/                      ← All 32 topic directories (19 original + 13 from splits)
│   ├── EXECUTION_PLAN.md
│   └── debate-index.md
│
└── tmp/                             ← Working area
    └── rebuild/                     ← This blueprint

─── OUTPUT TARGET (outside x38/) ───────────────────────────────
alpha_lab/genesis/                   ← Self-contained deliverable (per 07-genesis-pipeline.md)
├── README.md
└── specs/                           ← 18 spec files (1 per domain + entity_lifecycle)
```

---

## Verify Checklist

- [ ] 00-status.md created with all 6 sections (Domain Status, Deferred Items, Circular Deps, Integration Log, Spec Readiness, Export Readiness)
- [ ] Domain Status table populated from current state
- [ ] Deferred Items Registry populated (minimum: CVG-THR items)
- [ ] Circular Dependencies populated (minimum: 07<->17A)
- [ ] Integration Log has initial extraction entry (starts from rebuild date, not old closures)
- [ ] Spec Readiness table populated
- [ ] EXECUTION_PLAN.md moved to archive/
- [ ] debate-index.md moved to archive/
- [ ] PLAN.md header updated: "informational, check decisions/ for status"
- [ ] F-01 verified: no conflicting status tables exist outside 00-status.md
- [ ] F-02 verified: all 018 routing obligations reflected in consumer domain Constraints sections
- [ ] F-03 verified: all deferred items visible in single registry
- [ ] 17-epistemic-search.md included in decisions/ structure (6 findings across 2 sub-sections: 17A intra-campaign + 17B inter-campaign)
- [ ] 18-discovery-feedback-loop.md included in decisions/ structure (18 DFL findings across 9 sub-domains: 18A/B/C/D1/D2/D3/E/F/G)
- [ ] Live `debate/` tree created for open domains
- [ ] `debate/*/external/chatgpt_web/` lane defined for imported ChatGPT web input
- [ ] methodology_spec.md included in drafts/ structure
- [ ] Spec Readiness table reflects DRAFTING status for architecture, discovery, methodology specs
- [ ] Export Readiness table added with 19 genesis/ sections (per 07-genesis-pipeline.md)
