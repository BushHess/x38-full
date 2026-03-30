# 01 — New Taxonomy Design

> Solves: A-01, A-02, A-03, A-04, A-05
> Status: DRAFT

---

## Problem Summary

Current system has 2 labels: **Converged** and **Judgment Call (JC)**.
This conflates 4 fundamentally different decision types under "JC", making it impossible to assess decision quality, revisit risk, or provenance without re-reading full debate history.

Additionally:
- Routed findings from closed topics labeled "Open" (A-03)
- Finding IDs use inconsistent prefixes (A-04)
- Non-findings (precedent analysis) classified as findings (A-05)

---

## Solution: 5-Type Decision Classification

### Decision types (replaces Converged/JC binary)

| Type | Definition | Authority | Revisit risk |
|------|-----------|-----------|--------------|
| `CONVERGED` | Both agents agreed via steel-man protocol | Debate process | LOW — would need new evidence to reopen |
| `ARBITRATED` | Genuine disagreement, human researcher broke tie | Human (Tier 3) | MEDIUM — new evidence or context could change ruling |
| `AUTHORED` | No disagreement existed; human added spec detail | Human (Tier 3) | LOW — spec-tightening, not contested |
| `DEFAULT` | Conventional engineering choice, no controversy | Convention | LOW — standard practice |
| `DEFERRED` | Structurally blocked, decision postponed to named dependency | Pending | HIGH — must be resolved before spec publication |

### Rules

1. Every finding MUST have exactly 1 type.
2. Type is assigned at closure time by human researcher.
3. `DEFERRED` findings MUST specify: `blocked_by: [topic/finding ID]` and `unblocks: [spec section]`.
4. `ARBITRATED` findings MUST include 1-sentence rationale for which position was chosen.
5. `AUTHORED` findings MUST note what was added beyond agent consensus.

### Migration: Reclassify JCs from closed topics

> **AUDIT NOTE (2026-03-29)**: Original plan listed 17 JCs / 65 total findings.
> Self-audit revealed this was UNDERCOUNTED. Actual: 23+ JCs across 79 closed-topic
> findings + ~85 open-topic findings = ~164 total.
>
> **ACTION REQUIRED**: Before executing rebuild, extract COMPLETE finding list from
> every final-resolution.md and findings-under-review.md. The table below is PARTIAL
> and must be completed during Step 1 of rebuild execution.

#### Known JC reclassifications (17 verified)

| Current ID | Topic | New Type | Rationale |
|------------|-------|----------|-----------|
| D-16 | 001 | ARBITRATED | Genuine scope dispute, 2-axis separation |
| D-04-E | 002 | ARBITRATED | MK-03 criterion vs governance path |
| D-04-A | 002 | ARBITRATED | Vocabulary expansion vs discipline |
| D-04-B-auth | 002 | ARBITRATED | GAP/AMBIGUITY split adoption |
| D-04-B-cod | 002 | DEFAULT | Both agreed "don't split now" |
| MK-03 | 004 | AUTHORED | Human tightened context manifest |
| MK-04 | 004 | AUTHORED | Human added artifact fields for "Partially" verdict |
| MK-07 | 004 | AUTHORED | Human chose timing of vocabulary work |
| C1 | 004 | AUTHORED | Human added `semantic_status: PENDING` output field |
| C2 | 004 | AUTHORED | Human froze minimal schema, deferred calibration |
| D-23 | 010 | ARBITRATED | Scope 010 vs 008 |
| CA-01 | 013 | ARBITRATED | False dichotomy broken, scope boundary |
| CA-02 | 013 | DEFAULT | Bootstrap practical constants |
| SSE-09 | 013 | DEFAULT | Holm alpha=0.05 conventional |
| SSE-04-THR | 013 | DEFERRED | Circular 013<->017 dependency, blocked_by: 017 |
| D-03 | 001 | CONVERGED | Was mislabeled; agents agreed |
| SSE-D-05 | 018 | ARBITRATED | Evidence quality dispute |

#### Missing — must be extracted and reclassified

| Current ID | Topic | New Type | Notes |
|------------|-------|----------|-------|
| MK-12 | 004 | TBD | Confidence scoring — read final-resolution.md |
| MK-13 | 004 | TBD | Storage format — read final-resolution.md |
| MK-15 | 004 | TBD | Bootstrap problem — read final-resolution.md |
| MK-17 | 004 | TBD | Central question — read final-resolution.md |
| D-15 | 001 | TBD | Two cumulative scopes — verify if CONVERGED or JC |
| (others) | 013 | TBD | Topic 013 has 15 findings; verify all JC/Converged splits |

### Actual scale (corrected)

```
Closed topics (8):   ~79 findings (56 Converged + 23+ JC)
Open topics (10):    ~85 findings
TOTAL:               ~164 findings

JC breakdown (23+):  ~8 ARBITRATED, ~7 AUTHORED, ~4 DEFAULT, ~4 DEFERRED
```

> **The exact numbers will be known only after full extraction in rebuild Step 1.**

---

## Solution: Finding Status (replaces "Open"/"Closed")

| Status | Definition |
|--------|-----------|
| `OPEN` | Under active debate or awaiting debate |
| `DECIDED` | Decision made, binding within its topic |
| `INTEGRATED` | Decision verified against all consuming specs/topics |
| `CONSTRAINT` | Imported from a closed topic — not debatable, must be respected |

### Rules

1. Routed findings from closed topics enter as `CONSTRAINT`, never `OPEN`.
2. A finding cannot move to `INTEGRATED` until all downstream consumers acknowledge it.
3. `DEFERRED` decisions remain `DECIDED` (not `INTEGRATED`) until the blocking dependency resolves.

---

## Solution: Standardized Finding IDs

### Convention

```
X38-{DOMAIN}-{NN}
```

Where DOMAIN is a 2-4 letter code for the concept domain (not the topic number):

| Domain code | Concept |
|-------------|---------|
| `PHL` | Philosophy & mission |
| `CAM` | Campaign model |
| `IDV` | Identity & versioning |
| `FWL` | Firewall & contamination |
| `MKG` | Meta-knowledge governance |
| `OOS` | Clean OOS certification |
| `CVG` | Convergence analysis |
| `SSE` | Search-space expansion |
| `ENG` | Core engine |
| `FEA` | Feature engine |
| `PRO` | Protocol engine |
| `DAT` | Data integrity |
| `DEP` | Deployment boundary |
| `QAS` | Quality assurance |
| `EXE` | Execution & resilience |
| `RCL` | Bounded recalibration |
| `ESP` | Epistemic search policy |
| `ART` | Artifact & versioning |

### Migration: Create mapping table from old IDs to new IDs during extraction.

---

## Solution: Finding vs Non-Finding

### Definition of a finding

A finding MUST have:
1. **A design question** — a specific choice between 2+ alternatives
2. **At least 2 defensible positions** — otherwise it's a constraint or a fact
3. **An impact on spec content** — otherwise it's commentary

Items that fail these criteria become:
- **Supporting evidence** — input to other findings, not debatable on its own
- **Implementation note** — operational detail, deferred to build phase
- **Open question** — research question without proposed answer, tracked separately

### Migration: Topic 012 F-19 reclassified as "supporting evidence".

---

## Verify Checklist

- [ ] All 65 existing findings reclassified with new 5-type system
- [ ] All 17 former JCs have correct new type + rationale
- [ ] All routed findings marked CONSTRAINT (not OPEN)
- [ ] All finding IDs migrated to X38-{DOMAIN}-{NN} format
- [ ] Old-to-new ID mapping table complete
- [ ] F-19 (Topic 012) reclassified as supporting evidence
- [ ] D-03 (Topic 001) label contradiction resolved
