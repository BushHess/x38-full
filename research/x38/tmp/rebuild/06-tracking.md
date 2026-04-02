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
> Authoritative for: project status, deferred items, circular deps, integration log.

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
| 10-protocol-engine | 0 | 4 | 0 | ? | BLOCKED (waits 16,17,18) |
| 11-engine-design | 0 | 4 | 0 | 0 | ACTIVE (F-07 + ER-01/02/03) |
| 12-feature-engine | 0 | 3 | 0 | 1 | ACTIVE (F-08, F-38 + SSE-D-03) |
| 13-data-integrity | 0 | 2 | 0 | 0 | ACTIVE |
| 14-deployment | 0 | 2 | 0 | 0 | ACTIVE |
| 15-quality-assurance | 0 | 2 | 0 | 0 | ACTIVE (F-18, F-39; F-19 demoted) |
| 16-bounded-recalibration | 0 | 2 | 0 | 0 | ACTIVE (BR-01, BR-02) |
| 17-epistemic-search | 0 | 6 | 0 | 2 | ACTIVE (ESP-01→04 + SSE-08-CON, SSE-04-CELL) |
| 18-discovery-feedback-loop | 0 | 18 | 0 | 0 | ACTIVE (DFL-01→DFL-18, all deps satisfied) |

## Deferred Items Registry

| ID | Decision deferred | Blocked by | Unblocks | Provisional value |
|----|-------------------|------------|----------|-------------------|
| X38-CVG-THR | Convergence numeric floors | 17-epistemic-search | architecture §9.3 | methodology frozen, numerics TBD |
| X38-CVG-THR-3a | Robustness minimum numerics | 17-epistemic-search | architecture §9.4 | owned by convergence domain |
| ... | ... | ... | ... | ... |

## Circular Dependencies

| Pair | Interface | Resolution | Status |
|------|-----------|------------|--------|
| 07-convergence <-> 17-epistemic-search | metric methodology ↔ consumption criteria | PENDING | Cannot freeze until 17 has DECIDED findings. See 03-dependency-rules.md |
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
| architecture_spec.md | DRAFTING | 4 stubs + 1 proposal | 03-identity, 13-data, 16-recal, 17-esp; §14 proposal from 18-DFL |
| meta_spec.md | SEEDED (DRAFTING-READY) | 0 (transcription only) | none |
| discovery_spec.md | DRAFTING (partial) | §1-5 authoritative, §6-11 proposals | 18-discovery-feedback-loop (§6-§11 non-authoritative until 019 CLOSED) |
| methodology_spec.md | DRAFTING | 0 | none (from 013 closure) |
| protocol_spec.md | NOT STARTED | N/A | 10-protocol-engine |
| engine_spec.md | NOT STARTED | N/A | 11-engine-design |
| feature_spec.md | NOT STARTED | N/A | 12-feature-engine |
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
├── decisions/                       ← AUTHORITATIVE (18 domain files + 1 tracking file)
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
│   ├── 17-epistemic-search.md
│   └── 18-discovery-feedback-loop.md ← Topic 019 (18 findings, largest domain)
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
│   ├── debate/                      ← All 19 topic directories
│   ├── EXECUTION_PLAN.md
│   └── debate-index.md
│
└── tmp/                             ← Working area
    └── rebuild/                     ← This blueprint
```

---

## Verify Checklist

- [ ] 00-status.md created with all 5 sections
- [ ] Domain Status table populated from current state
- [ ] Deferred Items Registry populated (minimum: CVG-THR items)
- [ ] Circular Dependencies populated (minimum: 07<->17)
- [ ] Integration Log backfilled for all 8 closed topics
- [ ] Spec Readiness table populated
- [ ] EXECUTION_PLAN.md moved to archive/
- [ ] debate-index.md moved to archive/
- [ ] PLAN.md header updated: "informational, check decisions/ for status"
- [ ] F-01 verified: no conflicting status tables exist outside 00-status.md
- [ ] F-02 verified: all 018 routing obligations reflected in consumer domain Constraints sections
- [ ] F-03 verified: all deferred items visible in single registry
- [ ] 18-discovery-feedback-loop.md included in decisions/ structure (18 DFL findings)
- [ ] methodology_spec.md included in drafts/ structure
- [ ] Spec Readiness table reflects DRAFTING status for architecture, discovery, methodology specs
