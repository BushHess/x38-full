# 07 — Genesis Export Pipeline

> Solves: J-01, J-02, J-03
> Status: DRAFT

---

## Problem Summary

- No defined path from x38/decisions/ to alpha_lab/genesis/ (J-01)
- X40 has proven operational concepts (state machines) that x38 debate may not produce on its own (J-02)
- No abstraction test ensuring genesis/ is self-contained and asset-agnostic (J-03)

---

## Context

The rebuild's final deliverable is `alpha_lab/genesis/` — a self-contained
architecture specification, not x38/decisions/ itself. genesis/ must be
instantiable for any asset class without referencing x38, btc-spot-dev, or BTC.

```
x38/decisions/{domain}.md              ← debate arena
        │
        ▼  domain closes (INTEGRATED)
        │
   ┌────┴────┐
Standard  Lightweight
   │         │
x38/drafts/  (skip)
{spec}.md    │
   └────┬────┘
        │
        ▼  abstraction test + export gate
alpha_lab/genesis/specs/{domain}.md    ← self-contained output
```

---

## Solution 1: Genesis Export Contract (kills J-01)

### Genesis directory structure

```
alpha_lab/genesis/
├── README.md                       ← Purpose, scope, how to instantiate
└── specs/
    ├── philosophy.md               ← Core principles
    ├── campaign_model.md           ← Campaign→Session lifecycle
    ├── identity_versioning.md      ← Entity identity, version schema
    ├── firewall.md                 ← Contamination isolation rules
    ├── meta_knowledge.md           ← 3-tier taxonomy, lesson lifecycle
    ├── clean_oos.md                ← OOS policy, one-freeze-one-timeline
    ├── convergence.md              ← Convergence criteria, numeric methodology
    ├── search_expansion.md         ← Breadth-activation, routing
    ├── protocol_engine.md          ← Pipeline stages, stage gates, constraints
    ├── engine_design.md            ← Core engine API, execution model
    ├── feature_engine.md           ← Feature registry, generation modes
    ├── data_integrity.md           ← Data surface tiers, immutability
    ├── deployment.md               ← Deployment boundary, monitoring triggers
    ├── quality_assurance.md        ← Testing strategy, framework QA
    ├── bounded_recalibration.md    ← Requalification rules, operational cadence
    ├── epistemic_search.md         ← Consumption framework, search policy
    ├── discovery_feedback_loop.md  ← Data profiling, grammar, pre-filter, budget
    └── entity_lifecycle.md         ← State machines (baseline, durability, challenger)
```

19 files total (18 specs + README). Additional directories (contracts/,
schemas/, templates/) may emerge from debate — they are NOT pre-defined.

### Domain → Genesis mapping

| x38 domain | genesis/ target | Notes |
|------------|----------------|-------|
| 01-philosophy | specs/philosophy.md | Direct export |
| 02-campaign-model | specs/campaign_model.md | Direct export |
| 03-identity-versioning | specs/identity_versioning.md | Large — may split on export |
| 04-firewall | specs/firewall.md | Direct export |
| 05-meta-knowledge | specs/meta_knowledge.md | Direct export |
| 06-clean-oos | specs/clean_oos.md | Direct export |
| 07-convergence | specs/convergence.md | Direct export |
| 08-search-expansion | specs/search_expansion.md | Direct export |
| 10-protocol-engine | specs/protocol_engine.md | Integration hub — last to export |
| 11-engine-design | specs/engine_design.md | Direct export |
| 12-feature-engine | specs/feature_engine.md | Direct export |
| 13-data-integrity | specs/data_integrity.md | Includes data surface tier concepts |
| 14-deployment | specs/deployment.md | Direct export |
| 15-quality-assurance | specs/quality_assurance.md | Direct export |
| 16-bounded-recalibration | specs/bounded_recalibration.md | Direct export |
| 17-epistemic-search | specs/epistemic_search.md | Direct export |
| 18-discovery-feedback-loop | specs/discovery_feedback_loop.md | Direct export |
| X40-sourced (state machines) | specs/entity_lifecycle.md | See Solution 2 |

### Export gate (per genesis section)

A genesis/ section is EXPORTABLE when ALL of:

1. **ALL source domain(s) status ≥ INTEGRATED** — all findings DECIDED, all
   constraints imported. For multi-domain sections (entity_lifecycle.md from
   03 + 16), ALL source domains must independently satisfy this condition
2. **Content ready for export** — one of:
   - *Standard path*: owning spec section status ≥ REVIEW
   - *Lightweight path*: domain decisions directly assembled, internal consistency verified
3. **Abstraction test PASS** — see Solution 3
4. **No DEFERRED items block this section**
5. **genesis_target declared** — every source finding has explicit `genesis_target:` field

### Export procedure

**Standard path** (domain has mapped spec section in 05-spec-gates.md):
1. Domain reaches INTEGRATED status
2. Spec section(s) reach REVIEW status
3. Apply abstraction test (Solution 3)
4. Transform: parameterize BTC-specific content
5. Write genesis/ section
6. Cross-reference check: all pointers resolve within genesis/
7. Update 00-status.md export readiness table

**Lightweight path** (domain has no dedicated spec section — e.g., 01-philosophy,
06-clean-oos):
1. Domain reaches INTEGRATED status
2. Content assembled directly from domain decisions
3-7. Same as standard path

> During rebuild execution, each domain should be assigned to either path.

### Spec lifecycle extension

05-spec-gates.md lifecycle gains one terminal state:

```
SKELETON → PROPOSAL → DRAFTING → REVIEW → PUBLISHABLE → PUBLISHED → EXPORTED
```

EXPORTED = abstraction test passed, written to alpha_lab/genesis/.

A PUBLISHED section that fails the abstraction test stays PUBLISHED until fixed:
- **Spec-level fix**: rewrite to parameterize (e.g., "H4 bars" → "configurable resolution")
- **Decision-level fix**: if the source DECISION is too specific, use reopening
  protocol (03-dependency-rules.md Solution 5) to revise it

---

## Solution 2: X40 as Reference Material (kills J-02)

### Principle

X40 Pack v2 is **reference material** for x38 domain debates, not a formal
import source. Debate participants may cite X40 evidence like any other reference.
Most X40 concepts (comparison discipline, promotion ladder, operational cadence,
etc.) will emerge naturally during debate without special intake.

**Exception**: 3 state machine concepts represent a modeling discipline that
narrative debate is unlikely to produce on its own. These are recommended as
new findings during Step 0.

### 3 recommended concepts

| Concept | Why x38 lacks it | Target domain | genesis_target |
|---------|-----------------|---------------|----------------|
| Baseline lifecycle (states + transitions) | 03 has identity axes but no lifecycle progression | 03-identity-versioning | specs/entity_lifecycle.md |
| Durability assessment (health states + aggregation) | 16 has recalibration concept but no formal states | 16-bounded-recalibration | specs/entity_lifecycle.md |
| Challenger tracking (states + expiry rules) | 16 has no formal challenger management model | 16-bounded-recalibration | specs/entity_lifecycle.md |

During Step 0, evaluate each: if existing findings already cover the concept,
no action. If not, create a new finding using the standard format from
02-concept-structure.md (with genesis_target field). Use 01-taxonomy.md rules
for Type assignment (AUTHORED if directly adoptable, type TBD if debate needed).

> **Domain downgrade**: Adding a new OPEN finding to domain 03 (INTEGRATED)
> downgrades it to ACTIVE. Accept this cost only if the concept is genuinely
> missing — do not open trivial findings in closed domains.

### What to leave in X40 (not architecture)

| Category | Example | Why |
|----------|---------|-----|
| Concrete thresholds | MDD ≤ 0.45, 180 days | Configurable parameters |
| Instance names | OH0, PF0, PF1 | Runtime objects |
| Asset-specific logic | BTC regime rules, funding rates | Domain-specific |
| Operational routing | Decision tree Case A-H | Operational policy |
| File format details | baselines.yaml schema | Implementation |
| Specific cost values | 50 bps, 20 bps | Parameters |
| Fixed cadence | monthly/quarterly/annual | Schedule, not architecture |
| Specific promotion stages | DIAGNOSTIC→FILTER→EXIT_OVERLAY→STANDALONE | Let debate decide |

---

## Solution 3: Abstraction Test (kills J-03)

### Principle

genesis/ must be self-contained: readable and implementable WITHOUT access to
x38/, btc-spot-dev/, X40/, or any BTC-specific artifact.

### Test (applied per genesis section before EXPORTED status)

A section passes if ALL of:

1. **Zero prohibited references**: no x38, btc-spot-dev, X40, specific strategies
   (E0, E5, VTREND), specific assets (BTC, USDT), specific exchanges (Binance),
   or research study IDs (x12-x32)
2. **Self-referential**: all concepts defined within genesis/ or cross-referenced
   to other genesis/ sections
3. **Parameterized**: concrete values are parameters with defaults and valid ranges
4. **Domain-agnostic readability**: understandable without cryptocurrency knowledge
5. **Instantiation test**: could be instantiated for equities, FX, or commodities
   without structural modification

> Criteria 1-2 are mechanically verifiable. Criterion 3 is semi-automatable.
> Criteria 4-5 require human review.

### Abstraction patterns

| BTC-specific | genesis/ abstract | Pattern |
|-------------|-------------------|---------|
| OH0_D1_TREND40 | "baseline instance" | Instance → type |
| CP_PRIMARY_50_DAILYUTC | "comparison profile (params)" | Concrete → parameterized |
| OHLCV_ONLY / PUBLIC_FLOW / RICHER_DATA | "data surface tiers (configurable)" | Enum → extensible |
| B0→B1→B2→B_FAIL | "lifecycle state machine (configurable)" | Fixed FSM → configurable |
| 50 bps round-trip | "cost parameter" | Magic number → parameter |
| BTC/USDT H4 bars | "configurable resolution bars" | Asset-specific → generic |
| E5 EMA crossover | "entry signal (strategy-defined)" | Algorithm → interface |
| Wilcoxon p ≤ 0.10 | "statistical gate (pluggable)" | Fixed test → pluggable |

### genesis_target field

Every finding that produces genesis/ output MUST include:
```
genesis_target: specs/{section} | NONE
```

Added at extraction (Step 0) for existing findings, at creation for new findings.
A finding with `NONE` is process/governance — legitimate, not everything exports.

---

## Integration with existing rebuild documents

### 02-concept-structure.md
Finding templates gain `genesis_target:` field (already added).

### 05-spec-gates.md
Lifecycle extended with EXPORTED (already added).

### 06-tracking.md
00-status.md gains `## Export Readiness` section tracking 19 genesis/ files.
Step 0 extraction gains: assign genesis_target per finding, evaluate 3 X40
state machine concepts.

---

## Verify Checklist

- [ ] Genesis directory structure defined (specs/ + README = 19 files)
- [ ] All 17 domains + entity_lifecycle mapped to genesis/ targets
- [ ] Export gate defined (5 conditions, standard + lightweight paths)
- [ ] Export procedure defined (7 steps + lightweight variant)
- [ ] Spec lifecycle extended with EXPORTED status
- [ ] Abstraction test defined (5 criteria, 8 patterns)
- [ ] Abstraction test failure paths documented (spec-level + decision-level)
- [ ] X40 reference material guidance documented
- [ ] 3 state machine concepts identified (baseline, durability, challenger)
- [ ] What-to-leave-in-X40 list defined
- [ ] genesis_target field in finding format
- [ ] Cross-references to 02, 05, 06 documented
