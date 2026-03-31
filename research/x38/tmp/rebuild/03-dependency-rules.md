# 03 — Dependency & Ordering Rules

> Solves: C-01, C-02, C-03, C-04, C-05
> Status: DRAFT

---

## Problem Summary

- Topic 014 scheduled before its dependency (003) — C-01
- Topics 016/017 stuck as "backlog" despite satisfied deps — C-02
- 013<->017 circular dependency buried in JC, both marked "closed" — C-03
- No closure-to-integration workflow — C-04
- Topic 003 overloaded as integration hub with 16 cross-topic tensions — C-05

---

## Solution 1: Explicit Ordering Contract

### Principle
Every domain has a `depends_on` list and a `blocks` list. A domain CANNOT begin active debate on `## Open` findings until ALL `depends_on` domains have status >= DECIDED.

### Ordering DAG for rebuilt domains

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
  12-feature-engine        depends_on: [08]
  13-data-integrity        depends_on: [01]

Tier 3 (cross-cutting):
  16-bounded-recalibration depends_on: [02, 04, 06, 03, 14-deployment]
  17-epistemic-search      depends_on: [04, 06, 07]

Tier 4 (integration):
  10-protocol-engine       depends_on: [02, 03, 04, 05, 16, 17]
```

### Rules

1. **Activation trigger**: A domain activates when ALL items in `depends_on` have zero `OPEN` findings.
2. **No premature scheduling**: A domain with unmet deps stays in BLOCKED status.
   - Solves C-01: engine-design (old 005+014) is self-contained now.
   - Solves C-02: 016/017 activate when their deps are met — explicit trigger, not vague "backlog".
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

3. **Registry**: All circular dependencies tracked in `09-open-questions.md` under `## Circular Dependencies` with resolution status.

### Apply to C-03 (013<->017):

```
CIRCULAR: X38-CVG-THR (convergence numerics) <-> X38-ESP-?? (consumption framework)
Status: DETECTED
Resolution: PENDING — cannot freeze until 17-epistemic-search has DECIDED findings
```

> **AUDIT NOTE (2026-03-29)**: Original plan claimed "INTERFACE FREEZE" resolution.
> This is PREMATURE — Topic 017 has 16 OPEN findings, none decided. Cannot freeze
> an interface that doesn't exist yet.
>
> **Correct approach**:
> 1. During rebuild extraction: mark X38-CVG-THR as DEFERRED with `blocked_by: 17-epistemic-search`
> 2. Domain 07-convergence status = DECIDED (not INTEGRATED) — it has deferred items
> 3. When 17-epistemic-search decides its consumption framework:
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
- **Tracked in**: `09-open-questions.md` under `## Integration Log`

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

### Impact on 09-open-questions.md

Reopening events tracked in `## Integration Log` with type: REOPENED.

---

## Verify Checklist

- [ ] Ordering DAG documented with depends_on/blocks for all ~17 domains
- [ ] No domain has OPEN findings while its depends_on domains have OPEN findings
- [ ] C-01 resolved: engine-design is Tier 2, not prematurely scheduled
- [ ] C-02 resolved: 016/017 have explicit activation triggers
- [ ] C-03 resolved: 013<->017 circular in 09-open-questions.md with interface freeze
- [ ] C-04 resolved: 3-step closure workflow documented
- [ ] C-05 resolved: protocol-engine has constraints register
- [ ] All circular dependencies in 09-open-questions.md
