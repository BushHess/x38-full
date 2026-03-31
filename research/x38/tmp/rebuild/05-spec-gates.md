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
SKELETON -> DRAFTING -> REVIEW -> PUBLISHABLE -> PUBLISHED
```

| Status | Definition | Gate to advance |
|--------|-----------|-----------------|
| `SKELETON` | Section headers exist; content is placeholder or minimal | N/A (auto-created when first source domain closes) |
| `DRAFTING` | Content being written from DECIDED findings | Per-SECTION gate: a section advances to DRAFTING when its source domain has zero OPEN findings. Spec-level status = minimum across all sections |
| `REVIEW` | Full content written; awaiting cross-spec consistency check | ALL stubs filled; ALL provenance tags present; no DEFERRED items without explicit gates |
| `PUBLISHABLE` | Cross-spec consistency verified; human approved | Cross-spec audit passes; all DEFERRED items either resolved or explicitly gated |
| `PUBLISHED` | Moved to published/; read-only | Human final sign-off |

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
> **Blocked by**: 17-epistemic-search (consumption framework)
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
| architecture §9.2-9.4 | SSE-04-THR | Cited as frozen | Add: `DEFERRED, blocked_by: 17-epistemic-search, GATE` |
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
| `discovery_spec.md` | Recognition stack, equivalence audit, proof bundles, domain seeds, generation modes, APE | Breadth-activation contract interface (-> architecture_spec) |
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

| Spec | Section | Waiting on | Domain |
|------|---------|-----------|--------|
| architecture §4 | Data Management | X38-DAT-10, X38-DAT-11 | 13-data-integrity |
| architecture §8 | Deployment Boundary | X38-IDV-27/28/29 (merged) | 03-identity-versioning |
| architecture §10 | Bounded Recalibration | X38-RCL-34, X38-RCL-35 | 16-bounded-recalibration |
| architecture §11 | Epistemic Search | X38-ESP-01 through X38-ESP-06 | 17-epistemic-search |
| meta §2 | Lifecycle | Transcription from X38-MKG-* | 05-meta-knowledge (DONE) |
| meta §3 | Storage | Transcription from X38-MKG-* | 05-meta-knowledge (DONE) |

### Note on meta_spec §2/§3 (E-02)
Source domain (05-meta-knowledge) is fully DECIDED. These stubs are pure transcription debt — no blocking dependency. Can be filled immediately during rebuild.

---

## Verify Checklist

- [ ] Spec lifecycle updated to 5-tier (SKELETON/DRAFTING/REVIEW/PUBLISHABLE/PUBLISHED)
- [ ] All spec sections have provenance tags
- [ ] All DEFERRED provenance has GATE line
- [ ] Ownership map documented — no content in 2 specs
- [ ] architecture_spec vs discovery_spec boundary explicit (E-04 resolved)
- [ ] All stubs have resolution tracking (blocked_by + domain)
- [ ] meta_spec §2/§3 transcription marked as "ready now" (E-02)
- [ ] No spec can reach REVIEW with ungated DEFERRED sections
