# 03 — Dependency & Ordering Rules

> Solves: C-01, C-02, C-03, C-04, C-05
> Status: DRAFT

---

## Problem Summary

- Topic 014 scheduled before its dependency (003) — C-01
- Topics 016/017 stuck as "backlog" despite satisfied deps — C-02 (017 now SPLIT: 017A all deps satisfied, 017B waits 017A)
- 013<->017A circular dependency buried in JC, both marked "closed" — C-03
- No closure-to-integration workflow — C-04
- Topic 003 overloaded as integration hub with 16 cross-topic tensions — C-05

---

## Solution 1: Explicit Ordering Contract

### Principle
Every domain has a `depends_on` list and a `blocks` list. A domain CANNOT begin active debate on `## Open` findings until ALL `depends_on` domains have status >= DECIDED.

### Ordering DAG for rebuilt domains

> **UPDATE (2026-04-02)**: Added 18-discovery-feedback-loop (Topic 019, 18 findings).
> Fixed 10-protocol-engine depends_on to include 18 (per debate-index.md: 003 ← 019).

```
Tier 0 (no deps, DONE):
  01-philosophy

Tier 1 (deps on Tier 0, DONE):
  02-campaign-model        depends_on: [01]
  04-firewall              depends_on: [01]
  05-meta-knowledge        depends_on: [01]
  06-clean-oos             depends_on: [01]
  07-convergence           depends_on: [01]
  08-search-expansion      depends_on: [01]

Tier 2 (deps on Tier 0+1):
  03-identity-versioning   depends_on: [01, 02, 04]
  11-engine-design         depends_on: [01], soft_depends_on: [10-protocol-engine]
                           ← 005+014 merged. Engine API (005) self-contained.
                             Execution orchestration (014) may need revision
                             after protocol stages (010) finalize.
                             ER-03 (session concurrency, gap audit 2026-03-31) added.
  12-feature-engine        depends_on: [01, 08]
                           ← F-38 (feature family ontology, gap audit 2026-03-31) added.
                             01 (topic 007) was soft-dep for topic 006.
  13-data-integrity        depends_on: [01]
  14-deployment            depends_on: [01, 06]
                           ← From old 011 (F-26, F-27). Soft-dep on 007✅, 010✅.
  15-quality-assurance     depends_on: [01]
                           ← From old 012 (F-18, F-39). Soft-dep on 007✅, 008✅.

Tier 3 (cross-cutting):
  16-bounded-recalibration depends_on: [02, 04, 06, 03, 14-deployment]
  17A-intra-campaign-esp   depends_on: [04, 06, 07, 08] — ALL DEPS SATISFIED
                           ← ESP-01, ESP-04, SSE-04-CELL (3 findings).
                             013↔017A circular dep (CVG-THR). 003 needs 17A.
                             Also depends on topic 008 decisions (in domain 03),
                             but 03 has OPEN findings — see Note below.
  17B-inter-campaign-esp   depends_on: [17A] — waits 17A
                           ← ESP-02, ESP-03, SSE-08-CON (3 findings).
                             Can run parallel with 10-protocol-engine.
  18-discovery-feedback-loop depends_on: [08, 04, 05]
                           ← Topic 019. HARD-dep from 018✅ + 002✅ + 004✅.
                             All deps SATISFIED. Parallel with 016, 17A.
                             **SPLIT (2026-04-02)** → 9 sub-domains:
                             18A (foundations, debate FIRST) → 18B + 18C (parallel)
                             18A + 18B → 18D1 + 18D2 (parallel; 18C NOT blocking)
                             18D2 → 18D3 (sequential).
                             18E + 18F + 18G independent (parallel with all).
                             Feeds discovery_spec §6-§11, architecture_spec §14.

Tier 4 (integration):
  10-protocol-engine       depends_on: [02, 03, 04, 05, 16, 17A, 18A, 18D1]
                           ← 18 (DFL) added: discovery loop adds protocol interaction
                             points (per debate-index.md line 104-107).
```

> **DAG limitation — domain 03 implicit dependencies (2026-04-03)**:
> Several Tier 2+ domains (11-engine-design, 12-feature-engine, 13-data-integrity,
> 15-quality-assurance, 17A-intra-campaign-esp) have a SATISFIED dependency on
> Topic 008 (architecture-identity) decisions, which now reside in domain
> 03-identity-versioning. These are NOT listed in `depends_on` because domain 03
> also contains OPEN findings from Topics 011 and 015 — listing 03 would trigger
> false blocking via the activation rule. The Topic 008 decisions are DECIDED and
> available as CONSTRAINTS. This is a known trade-off of domain-level (vs
> finding-level) granularity in the DAG.

### Rules

1. **Activation trigger**: A domain activates when ALL items in `depends_on` have zero `OPEN` findings.
2. **Soft dependencies**: `soft_depends_on` does NOT block activation. The domain may begin debate, but findings that touch the soft dependency's outputs are marked PROVISIONAL and must be re-verified after the soft dependency closes. Tracked in `00-status.md` Integration Log as type: REVISION_CHECK.
3. **No premature scheduling**: A domain with unmet deps stays in BLOCKED status.
   - Solves C-01: engine-design (old 005+014) is self-contained now.
   - Solves C-02: 016/017A/017B activate when their deps are met — explicit trigger, not vague "backlog".
3. **Integration hub rule**: Domain 10-protocol-engine debates LAST. It consumes, does not produce constraints for other domains.
   - Solves C-05: 003 is explicitly the final integrator, expected to have many constraints.

---

## Solution 2: Circular Dependency Resolution Protocol

### Principle
Circular dependencies MUST be surfaced and resolved BEFORE either domain closes.

### Protocol

1. **Detection**: When domain A defers an item "blocked_by: domain B" AND domain B has a finding that "depends_on: domain A" — flag as CIRCULAR.

2. **Resolution options** (choose one):
   - **Joint session**: Both domains debate the shared item together in a single round. Decision goes into BOTH domain files as DECIDED.
   - **Interface freeze**: Both domains agree on a minimal interface contract. Each domain can close independently as long as the interface is respected. Details deferred to integration.
   - **Merge**: If the circular items are really 1 decision, merge the findings into 1 domain.

3. **Registry**: All circular dependencies tracked in `00-status.md` under `## Circular Dependencies` with resolution status.

### Apply to C-03 (013<->017A):

```
CIRCULAR: X38-CVG-THR (convergence numerics) <-> X38-ESP-01/04 (consumption framework, 017A)
Status: DETECTED
Resolution: PENDING — cannot freeze until 17A-intra-campaign-esp has DECIDED findings
Note: 017 SPLIT (2026-04-03) into 017A (v1) + 017B (v2). Circular dep is with 017A only.
      017B (inter-campaign) does not interact with convergence numerics.
```

> **AUDIT NOTE (2026-03-29)**: Original plan claimed "INTERFACE FREEZE" resolution.
> This is PREMATURE — Topic 017A has 3 OPEN findings (ESP-01, ESP-04, SSE-04-CELL),
> none decided. Cannot freeze an interface that doesn't exist yet.
>
> **Correct approach**:
> 1. During rebuild extraction: mark X38-CVG-THR as DEFERRED with `blocked_by: 17A-intra-campaign-esp`
> 2. Domain 07-convergence status = DECIDED (not INTEGRATED) — it has deferred items
> 3. When 17A-intra-campaign-esp decides its consumption framework:
>    - THEN propose interface freeze
>    - THEN hold joint session to resolve numerics
>    - THEN both domains can reach INTEGRATED
> 4. Until then: 07-convergence's numeric sections are explicitly PROVISIONAL
>    in any spec that consumes them

---

## Solution 3: Closure-to-Integration Workflow

### Principle
When a domain's `## Open` section becomes empty (all findings DECIDED), it does NOT silently close. Instead:

### 3-step closure process

**Step 1: Domain internally complete**
- All `## Open` findings moved to `## Decided`
- All `## Deferred` items have explicit `blocked_by`
- Human researcher reviews and approves

**Step 2: Downstream notification**
- For each domain that lists this domain in `depends_on`:
  - Add new `## Constraints` entries for relevant decisions
  - Verify no contradictions with existing findings
- For each spec that consumes decisions from this domain:
  - Update spec section from stub to content (or mark as ready)
- **Tracked in**: `00-status.md` under `## Integration Log`

**Step 3: Status update**
- Domain status: DECIDED -> INTEGRATED (after Step 2 complete)
- Single ledger update (see 06-tracking.md)

### Solves C-04:
Every closure triggers explicit downstream notification. No more "Topic 018 closed but Topics 003/006 don't know".

---

## Solution 4: Constraints Register for Integration Hub

### Principle
Domain 10-protocol-engine (old Topic 003) gets a dedicated `## Constraints Register` section that is the single inventory of everything it must respect.

### Format

```markdown
## Constraints Register

| ID | From domain | Decision | Impact on protocol | Verified |
|----|-------------|----------|--------------------|----------|
| X38-CAM-03 | 02-campaign | Campaign = frozen properties | Stage 7 freeze contract | [ ] |
| X38-FWL-04 | 04-firewall | 3 F-06 categories only | Stage 2 filter whitelist | [ ] |
| X38-SSE-04 | 08-search | 7-field activation contract | Stage 1 activation gate | [ ] |
| ... | ... | ... | ... | ... |
```

### Rules
1. Register is updated during Step 2 of closure workflow.
2. Protocol engine debate ONLY begins when register has zero unverified rows.
3. If any upstream domain reopens, affected register rows revert to unverified.

---

## Solution 5: Reopening Protocol

### Principle
A DECIDED or INTEGRATED finding may need to reopen when new evidence
contradicts it, a downstream domain discovers an incompatibility, or
a circular dependency resolution invalidates prior assumptions.

### Conditions for reopening

A finding MAY be reopened if ANY of:
1. **New evidence**: a completed analysis (DFL-06/07) produces results
   that contradict the finding's rationale
2. **Downstream conflict**: a consuming domain discovers the finding
   creates an unresolvable contradiction with another DECIDED finding
3. **Circular resolution**: a joint session (Solution 2) produces a
   result incompatible with the finding

A finding MUST NOT be reopened merely because:
- An agent disagrees with the decision (debate is closed)
- A new team member would have decided differently (respect prior work)

### Reopening workflow

1. **Request**: Human researcher files reopening request with: finding ID,
   reason, new evidence, impact assessment
2. **Impact analysis**: List all downstream consumers (domain constraints,
   spec sections) that would be affected
3. **Status rollback**:
   - Finding: DECIDED → OPEN (or INTEGRATED → DECIDED if only
     cross-domain verification is needed)
   - Domain status: may regress (INTEGRATED → DECIDED or DECIDED → ACTIVE)
   - Downstream domains: affected constraint entries marked UNVERIFIED
   - Spec sections: affected provenance tags marked REOPENED
4. **Re-debate**: Finding re-enters `## Open` section of its domain file
5. **Re-closure**: Normal closure workflow (Solution 3) applies

### Impact on 00-status.md

Reopening events tracked in `## Integration Log` with type: REOPENED.

---

## Verify Checklist

- [ ] Ordering DAG documented with depends_on/blocks for all ~18 domains (including 18-DFL)
- [ ] No domain has OPEN findings while its depends_on domains have OPEN findings
- [ ] C-01 resolved: engine-design is Tier 2, not prematurely scheduled
- [ ] C-02 resolved: 016/017A/017B have explicit activation triggers
- [ ] C-03 resolved: 013<->017A circular DETECTED in 00-status.md, resolution PENDING until 17A has DECIDED findings
- [ ] C-04 resolved: 3-step closure workflow documented
- [ ] C-05 resolved: protocol-engine has constraints register
- [ ] All circular dependencies in 00-status.md
