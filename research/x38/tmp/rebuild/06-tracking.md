# 06 — Single-Source Tracking

> Solves: F-01, F-02, F-03
> Status: DRAFT

---

## Problem Summary

- PLAN.md vs EXECUTION_PLAN.md vs debate-index.md diverge on topic counts and status (F-01)
- Topics 003/006 not synced with Topic 018 routing obligations (F-02)
- Deferred items scattered across individual final-resolution.md files, no global view (F-03)

---

## Solution: Single Ledger in 09-open-questions.md

### Principle
ONE file tracks all dynamic state. Domain decision files track static state (decided findings). The only file that changes frequently is `09-open-questions.md`.

### Structure of 09-open-questions.md

```markdown
# Open Questions & Project Tracking

## Domain Status

| Domain | Decided | Open | Deferred | Constraints | Status |
|--------|---------|------|----------|-------------|--------|
| 01-philosophy | 4 | 0 | 0 | 0 | INTEGRATED |
| 02-campaign-model | 6 | 0 | 0 | 0 | INTEGRATED |
| 03-identity-versioning | 5 | 3 | 0 | 3 | ACTIVE |
| 04-firewall | 10 | 0 | 0 | 0 | INTEGRATED |
| 05-meta-knowledge | 12 | 0 | 0 | 0 | INTEGRATED |
| 06-clean-oos | 4 | 0 | 0 | 0 | INTEGRATED |
| 07-convergence | 6 | 0 | 2 | 0 | DECIDED (deferred items) |
| 08-search-expansion | 11 | 0 | 0 | 0 | INTEGRATED |
| 10-protocol-engine | 0 | 1 | 0 | 5+ | BLOCKED |
| 11-engine-design | 0 | 2 | 0 | 0 | ACTIVE |
| ... | ... | ... | ... | ... | ... |

## Deferred Items Registry

| ID | Decision deferred | Blocked by | Unblocks | Provisional value |
|----|-------------------|------------|----------|-------------------|
| X38-CVG-THR | Convergence numeric floors | 17-epistemic-search | architecture §9.3 | methodology frozen, numerics TBD |
| X38-CVG-THR-3a | Robustness minimum numerics | 17-epistemic-search | architecture §9.4 | owned by convergence domain |
| ... | ... | ... | ... | ... |

## Circular Dependencies

| Pair | Interface | Resolution | Status |
|------|-----------|------------|--------|
| 07-convergence <-> 17-epistemic-search | metric methodology ↔ consumption criteria | INTERFACE FREEZE | Numerics joint session after both decide methodology |
| ... | ... | ... | ... |

## Integration Log

| Date | Domain closed | Downstream updates | Verified by |
|------|--------------|-------------------|-------------|
| 2026-03-21 | 05-meta-knowledge (was Topic 004) | architecture §7 MK-14 boundary | human |
| 2026-03-23 | 02-campaign-model (was Topic 001) | 07-convergence constraints, 16-recalibration constraints | human |
| 2026-03-25 | 04-firewall (was Topic 002) | 17-epistemic constraints, 03-identity constraints | human |
| ... | ... | ... | ... |

## Spec Readiness

| Spec | Status | Stubs remaining | Blocking domains |
|------|--------|----------------|------------------|
| architecture_spec.md | SKELETON | 4 | 03-identity, 13-data, 16-recal, 17-esp |
| meta_spec.md | DRAFTING-READY | 0 (transcription only) | none |
| discovery_spec.md | SKELETON | 0 | none (review needed) |
| protocol_spec.md | NOT STARTED | N/A | 10-protocol-engine |
| engine_spec.md | NOT STARTED | N/A | 11-engine-design |
| feature_spec.md | NOT STARTED | N/A | 12-feature-engine |
```

---

## How this solves each issue

### F-01 (PLAN vs EXECUTION_PLAN vs debate-index diverge)

**Before**: 3 files with overlapping status tables, manually synced, persistently drifting.
**After**: 1 file (09-open-questions.md) has the `## Domain Status` table. PLAN.md is narrative-only with header "check decisions/ for status". EXECUTION_PLAN.md and debate-index.md archived.

### F-02 (003/006 not synced with 018 routing)

**Before**: Topic 018 closes, routing obligations scattered in its final-resolution.md. Consumer topics must self-update. 003/006 didn't.
**After**: Closure workflow (03-dependency-rules.md, Solution 3) requires explicit downstream update. Integration Log in 09-open-questions.md tracks that update happened. If 003/006 equivalent domains don't have constraints entries, Integration Log shows gap.

### F-03 (Deferred items scattered)

**Before**: Deferred decisions buried in individual final-resolution.md. No global view.
**After**: `## Deferred Items Registry` in 09-open-questions.md. Single table of all deferred items with blocked_by, unblocks, provisional value.

---

## Update Rules

### Who updates 09-open-questions.md

1. **Domain Status table**: Updated by human researcher after each domain closure (Step 3 of closure workflow).
2. **Deferred Items Registry**: Updated when a finding is classified DEFERRED (at closure time).
3. **Circular Dependencies**: Updated when detected (during debate or closure).
4. **Integration Log**: Updated during Step 2 of closure workflow (downstream notification).
5. **Spec Readiness**: Updated when spec status changes (stub filled, readiness gate met).

### Frequency
- This file changes ~1-2 times per week during active debate.
- It is the ONLY frequently-changing governance file.
- All other files (PLAN.md, domain files, spec files) change less frequently.

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
├── decisions/                       ← AUTHORITATIVE
│   ├── 01-philosophy.md
│   ├── 02-campaign-model.md
│   ├── 03-identity-versioning.md
│   ├── 04-firewall.md
│   ├── 05-meta-knowledge.md
│   ├── 06-clean-oos.md
│   ├── 07-convergence.md
│   ├── 08-search-expansion.md
│   ├── 09-open-questions.md         ← Single ledger (status, deferred, circular, log)
│   ├── 10-protocol-engine.md
│   ├── 11-engine-design.md
│   ├── 12-feature-engine.md
│   ├── 13-data-integrity.md
│   ├── 14-deployment.md
│   ├── 15-quality-assurance.md
│   ├── 16-bounded-recalibration.md
│   └── 17-epistemic-search.md
│
├── drafts/                          ← Spec drafts (consume decisions/)
│   ├── README.md                    ← Lifecycle rules
│   ├── architecture_spec.md
│   ├── meta_spec.md
│   ├── discovery_spec.md
│   └── ... (future specs)
│
├── published/                       ← Final specs (read-only)
│
├── archive/                         ← OLD structure (read-only reference)
│   ├── debate/                      ← All 19 topic directories
│   ├── EXECUTION_PLAN.md
│   └── debate-index.md
│
└── tmp/                             ← Working area
    └── rebuild/                     ← This blueprint
```

---

## Verify Checklist

- [ ] 09-open-questions.md created with all 5 sections
- [ ] Domain Status table populated from current state
- [ ] Deferred Items Registry populated (minimum: CVG-THR items)
- [ ] Circular Dependencies populated (minimum: 07<->17)
- [ ] Integration Log backfilled for all 8 closed topics
- [ ] Spec Readiness table populated
- [ ] EXECUTION_PLAN.md moved to archive/
- [ ] debate-index.md moved to archive/
- [ ] PLAN.md header updated: "informational, check decisions/ for status"
- [ ] F-01 verified: no conflicting status tables exist outside 09-open-questions.md
- [ ] F-02 verified: all 018 routing obligations reflected in consumer domain Constraints sections
- [ ] F-03 verified: all deferred items visible in single registry
