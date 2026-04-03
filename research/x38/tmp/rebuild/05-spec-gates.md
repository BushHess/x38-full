# 05 — Spec Integrity Gates

> Solves: E-01, E-02, E-03, E-04, E-05
> Status: DRAFT

---

## Problem Summary

- architecture_spec.md has 6 stub sections with no publication gate (E-01)
- meta_spec.md stubs not transcribed despite source topic closed (E-02)
- Deferred JCs embedded in specs as if frozen (E-03)
- Discovery ownership ambiguous between architecture_spec and discovery_spec (E-04)
- No spec-readiness tiers — "SEEDED" too vague (E-05)

---

## Solution 1: Spec Readiness Tiers (kills E-01, E-05)

### Current lifecycle
```
SEEDED -> DRAFTING -> PUBLISHABLE -> PUBLISHED
```

### New lifecycle
```
SKELETON -> PROPOSAL -> DRAFTING -> REVIEW -> PUBLISHABLE -> PUBLISHED -> EXPORTED
```

| Status | Definition | Gate to advance |
|--------|-----------|-----------------|
| `SKELETON` | Section headers exist; content is placeholder or minimal | N/A (auto-created when first source domain closes) |
| `PROPOSAL` | Content drafted from OPEN-topic findings; explicitly non-authoritative. May be superseded when source domain closes | Source domain has OPEN findings AND has produced enough material to draft preliminary content |
| `DRAFTING` | Content being written from DECIDED findings | Per-SECTION gate: a section advances to DRAFTING when its source domain has zero OPEN findings. Spec-level status = minimum across all sections |
| `REVIEW` | Full content written; awaiting cross-spec consistency check | ALL stubs filled; ALL provenance tags present; no DEFERRED items without explicit gates |
| `PUBLISHABLE` | Cross-spec consistency verified; human approved | Cross-spec audit passes; all DEFERRED items either resolved or explicitly gated |
| `PUBLISHED` | Moved to published/; read-only | Human final sign-off |
| `EXPORTED` | Abstraction test passed; written to alpha_lab/genesis/ | Abstraction test (07-genesis-pipeline.md Solution 3): zero prohibited references, parameterized values, domain-agnostic, self-referential within genesis/ |

> **NOTE (2026-04-02)**: EXPORTED added per 07-genesis-pipeline.md (J-01, J-03).
> A PUBLISHED section that fails the abstraction test stays PUBLISHED but cannot
> advance to EXPORTED. Fix = parameterize and remove BTC-specific references.

### Gate enforcement

A spec **section** CANNOT advance from SKELETON to DRAFTING while:
- Its source domain has OPEN findings
- Its source domain has DEFERRED items that affect this section

A spec's **overall status** = minimum across all its sections.
Individual sections may be at DRAFTING while others are still SKELETON.
This allows progressive drafting as domains close one by one.

A spec CANNOT advance from DRAFTING to REVIEW while:
- Any section is still SKELETON
- Any DEFERRED finding affects a non-gated section

---

## Solution 2: Provenance Tags (kills E-03)

### Principle
Every spec section sourced from a finding carries a provenance tag showing decision authority and status.

### Format (inline in spec)

```markdown
## §7.1 Firewall Enforcement

> **Provenance**: X38-FWL-04 (ARBITRATED, DECIDED)
> **Source debate**: Topic 002, Round 6
> **Revisit risk**: MEDIUM — vocabulary scope was contested

[section content...]
```

For DEFERRED items:

```markdown
## §9.3 Convergence Numeric Floors

> **Provenance**: X38-CVG-THR (DEFERRED)
> **Blocked by**: 17A-intra-campaign-esp (consumption framework)
> **Provisional value**: methodology frozen, exact numerics TBD
> **GATE**: This section CANNOT advance to REVIEW until X38-CVG-THR resolves.

[provisional content with explicit TBD markers...]
```

### Rules

1. Every spec section MUST have a `> Provenance:` block.
2. Provenance includes: finding ID, decision type, status, revisit risk.
3. DEFERRED provenance MUST include `GATE:` line specifying what blocks advancement.
4. Specs with ANY ungated DEFERRED sections cannot reach REVIEW status.

### Apply to current E-03 violations:

| Spec section | Finding | Current treatment | Correct treatment |
|-------------|---------|-------------------|-------------------|
| architecture §7.1 | MK-07 | Cited as frozen | Add: `AUTHORED, DECIDED, risk LOW` |
| architecture §9.2-9.4 | SSE-04-THR | Cited as frozen | Add: `DEFERRED, blocked_by: 17A-intra-campaign-esp, GATE` |
| discovery §2 | SSE-D-05 | Cited as authoritative | Add: `ARBITRATED, DECIDED, risk MEDIUM — working minimum, not immutable` |

---

## Solution 3: Spec Ownership Map (kills E-04)

### Principle
Each concept is owned by exactly 1 spec. Cross-spec references use `## See also` pointers, never duplicate content.

### Ownership map

| Spec | Owns | Does NOT own |
|------|------|-------------|
| `architecture_spec.md` | Campaign model, identity schema, firewall enforcement, deployment boundary, convergence rules, protocol pipeline stages | Discovery mechanisms (-> discovery_spec), meta-knowledge content rules (-> meta_spec) |
| `meta_spec.md` | 3-tier taxonomy, lesson lifecycle, storage law, derivation test, firewall content rules (whitelist categories) | Firewall enforcement (-> architecture_spec) |
| `discovery_spec.md` | Recognition stack, equivalence audit, proof bundles, domain seeds, generation modes, APE, **data profiling, grammar expansion, pre-filter, statistical budget, human-AI loop, feature graduation** (§6-§11 from DFL) | Breadth-activation contract interface (-> architecture_spec), discovery pipeline routing contract (-> architecture_spec §14) |
| `protocol_spec.md` (future) | 8-stage pipeline, stage gates, artifact enumeration | Engine API (-> engine_spec), feature registry (-> feature_spec) |
| `engine_spec.md` (future) | Core engine API, vectorized vs event-loop, parallelization | Protocol stages (-> protocol_spec) |
| `feature_spec.md` (future) | Feature registry pattern, generation mode acceptance | Discovery generation (-> discovery_spec) |

### Boundary rules

1. **Interface principle**: architecture_spec defines contracts (interfaces). Other specs define implementations.
   - Example: architecture_spec §12 defines breadth-activation contract fields. discovery_spec §3 defines how those fields are populated.

2. **No duplication**: If content appears in 2 specs, one MUST be a `> See also: [spec_name §N]` pointer.

3. **Ownership disputes**: If 2 specs both claim a section, escalate to human researcher. Default: architecture_spec owns contracts, domain-specific spec owns implementation.

---

## Solution 4: Stub Resolution Tracking (kills E-01, E-02)

### Principle
Every SKELETON stub is tracked with its resolution dependency.

### Format (in spec file)

```markdown
## §4 Data Management & Immutability

> **Status**: SKELETON
> **Blocked by**: 13-data-integrity domain (OPEN findings remain)
> **Estimated readiness**: When X38-DAT-10, X38-DAT-11 reach DECIDED

_Content pending._
```

### Current stubs and their resolution paths

> **UPDATE (2026-04-02)**: Added DFL-sourced sections for discovery_spec and
> architecture_spec. Status updated to match drafts/README.md 2026-04-01 state.

| Spec | Section | Waiting on | Domain | Status |
|------|---------|-----------|--------|--------|
| architecture §4 | Data Management | X38-DAT-10, X38-DAT-11 | 13-data-integrity | SKELETON |
| architecture §8 | Deployment Boundary | X38-IDV-27/28/29 (merged) | 03-identity-versioning | SKELETON |
| architecture §10 | Bounded Recalibration | X38-RCL-34, X38-RCL-35 | 16-bounded-recalibration | SKELETON |
| architecture §11 | Epistemic Search | X38-ESP-01, ESP-04 (017A) + ESP-02, ESP-03 (017B) | 17-epistemic-search (SPLIT: 17A intra + 17B inter) | SKELETON |
| architecture §14 | Discovery Pipeline Routing | X38-DFL-* (Topic 019) | 18-discovery-feedback-loop | PROPOSAL (non-authoritative) |
| discovery §1-§5 | v1 (bounded ideation, recognition stack, APE, etc.) | Topic 018 (CLOSED) | 08-search-expansion | DRAFTING (authoritative) |
| discovery §6-§11 | v2 (data profiling, grammar, pre-filter, budget, loop, graduation) | X38-DFL-01→DFL-18 (Topic 019 OPEN) | 18-discovery-feedback-loop | PROPOSAL (non-authoritative until 019 CLOSED) |
| meta §2 | Lifecycle | Transcription from X38-MKG-* | 05-meta-knowledge (DONE) | TRANSCRIPTION-READY |
| meta §3 | Storage | Transcription from X38-MKG-* | 05-meta-knowledge (DONE) | TRANSCRIPTION-READY |

### Note on meta_spec §2/§3 (E-02)
Source domain (05-meta-knowledge) is fully DECIDED. These stubs are pure transcription debt — no blocking dependency. Can be filled immediately during rebuild.

### Note on discovery_spec §6-§11 and architecture_spec §14
These sections contain **proposals** from Topic 019 (DFL-01→DFL-18), explicitly marked
as non-authoritative in drafts/README.md. They will advance from PROPOSAL to DRAFTING
only after Topic 019 closes. This is consistent with the SEEDED→DRAFTING gate
(per-section, source domain must have zero OPEN findings).

---

## Verify Checklist

- [ ] Spec lifecycle updated to 7-tier (SKELETON/PROPOSAL/DRAFTING/REVIEW/PUBLISHABLE/PUBLISHED/EXPORTED)
- [ ] All spec sections have provenance tags
- [ ] All DEFERRED provenance has GATE line
- [ ] Ownership map documented — no content in 2 specs
- [ ] architecture_spec vs discovery_spec boundary explicit (E-04 resolved)
- [ ] All stubs have resolution tracking (blocked_by + domain)
- [ ] meta_spec §2/§3 transcription marked as "ready now" (E-02)
- [ ] No spec can reach REVIEW with ungated DEFERRED sections
- [ ] EXPORTED status added with abstraction test gate (per 07-genesis-pipeline.md)
- [ ] All spec sections have genesis_target (per 07-genesis-pipeline.md, 02-concept-structure.md)
