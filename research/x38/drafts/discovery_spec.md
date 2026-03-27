# Discovery Specification — Alpha-Lab Framework

**Status**: SEEDED (2026-03-27, from Topic 018 closure)
**Source**: `debate/018-search-space-expansion/final-resolution.md`
**Dependencies**: Topic 018 (CLOSED) — primary source for all sections

> This spec covers discovery mechanisms: how Alpha-Lab generates, recognizes,
> and integrates new candidates. All sections trace to Topic 018 decisions.
> Downstream topics (006, 013, 015, 017) own thresholds, formulas, and
> consumption semantics — this spec defines the structural contracts they consume.

---

## §1 Bounded Ideation (SSE-D-02, SSE-D-03)

### 1.1 Hard Rules

All ideation (pre-lock candidate generation) must satisfy 4 hard rules:

1. **Results-blind** — ideation sees NO results from any session (past or current)
2. **Compile-only** — output must compile (syntactically valid strategy spec)
3. **OHLCV-only** — only OHLCV + volume data as input features
4. **Provenance-tracked** — every generated candidate records its generation method

Violation of any rule = candidate rejected at generation gate. No exceptions.

### 1.2 Generation Modes

Two modes available at protocol lock:

| Mode | Activation | Description |
|------|-----------|-------------|
| `grammar_depth1_seed` | Always available (mandatory default) | Deterministic grammar enumeration producing depth-1 seeds from declared building blocks |
| `registry_only` | Conditional — requires 3 guards | Re-use candidates from existing registry without new generation |

### 1.3 Cold-Start Activation (`registry_only`)

`registry_only` mode requires ALL 3 conditions:
1. Registry is **non-empty** (at least 1 candidate exists)
2. Registry is **frozen** (no active modifications)
3. Registry is **`grammar_hash`-compatible** (structural compatibility verified)

If any condition fails, fall back to `grammar_depth1_seed`.

### 1.4 Grammar-Provenance Admissibility

Grammar-provenance admissibility policing (what constitutes valid provenance
for a generated candidate) belongs in Topics 002/004 (contamination firewall),
not in the discovery spec. This spec defines generation modes; the firewall
spec defines what provenance records are admissible.

**Trace**: SSE-D-02, SSE-D-03 → `debate/018-search-space-expansion/final-resolution.md` Decision 2

---

## §2 Recognition Stack (SSE-D-05)

### 2.1 Pre-Freeze Recognition Topology

The recognition pipeline processes unexpected results through 4 stages:

```
surprise_queue → equivalence_audit → proof_bundle → freeze
```

- **surprise_queue**: Candidates flagged by anomaly detection enter a queue
  for structured evaluation
- **equivalence_audit**: Determines whether a surprise is genuinely novel
  or equivalent to a known candidate (uses hybrid equivalence per §5)
- **proof_bundle**: Assembles required evidence for the surprise candidate
  (5 proof components, see §2.3)
- **freeze**: Candidate promoted to frozen status with complete proof bundle

**Topology boundary**: This pipeline stops at `freeze`. Post-freeze stages
(`freeze_comparison_set → candidate_phenotype → contradiction_registry`) are
scoped to downstream topics (017, 003, 015) and are NOT part of the discovery
spec.

### 2.2 Working Minimum Inventory — Anomaly Axes

5 anomaly axes define the dimensions along which surprise is detected:

1. `decorrelation_outlier` — candidate returns decorrelated from known families
2. `plateau_width_champion` — candidate shows unusually wide parameter plateau
3. `cost_stability` — candidate performance unusually stable across cost scenarios
4. `cross_resolution_consistency` — candidate consistent across timeframe resolutions
5. `contradiction_resurrection` — candidate contradicts a previously dismissed hypothesis

### 2.3 Working Minimum Inventory — Proof Components

5 proof components required for a surprise candidate's proof bundle:

1. `nearest_rival_audit` — comparison against closest known candidate
2. `plateau_stability_extract` — evidence of parameter stability
3. `cost_sensitivity_test` — performance across cost scenarios
4. `dependency_stressor` — robustness under dependency perturbation
   (alias: `ablation_or_perturbation_test` — valid concrete form)
5. `contradiction_profile` — relationship to contradicted prior results

### 2.4 Inventory Governance

- The 5+5 named inventory is a **working minimum** adopted at **Judgment call
  authority** (not Converged). It is NOT an immutable historically-converged
  exact label set.
- **Thresholds**: Owned by Topics 017 (epistemic search policy) and 013
  (convergence analysis). This spec defines WHAT is measured, not HOW MUCH
  is enough.
- **Expansion**: Adding axes or components beyond the minimum requires an
  explicit downstream finding. The minimum is a floor, not a ceiling.

**Trace**: SSE-D-05 → `debate/018-search-space-expansion/final-resolution.md` Decision 4 → human researcher judgment

---

## §3 APE v1 Scope (SSE-D-11)

### 3.1 Template Parameterization Only

APE (Automated Parameter Exploration) v1 is limited to:
- Filling declared template parameters with values from declared ranges
- Producing candidates that satisfy all 4 hard rules (§1.1)

### 3.2 Excluded from v1

- **No free-form code generation** — correctness guarantee absent in v1
- **No indicator composition** — no combining arbitrary indicators into new ones
- **No runtime code evaluation** — all generation is compile-time only

### 3.3 v2+ Pathway

Free-form code generation is a v2+ capability, gated on:
- A verification mechanism being designed and validated
- Firewall integration for generated code provenance

**Trace**: SSE-D-11 → `debate/018-search-space-expansion/final-resolution.md` Decision 10

---

## §4 Domain-Seed Hook (SSE-D-10)

### 4.1 Optional Provenance Hook

Domain-seed is an **optional** provenance hook that records the domain context
(e.g., "this candidate was inspired by mean-reversion literature") as metadata.

### 4.2 Excluded

- **No replay semantics** — domain-seed does not enable replaying a generation process
- **No session format** — no structured session representation for domain seeds
- **No catalog infrastructure** — no centralized domain-seed registry

### 4.3 Composition Provenance

Composition provenance (how components were combined to form a candidate) is
preserved via lineage tracking (SSE-D-07, routed to Topic 015), not through
domain-seed replay.

**Trace**: SSE-D-10 → `debate/018-search-space-expansion/final-resolution.md` Decision 9

---

## §5 Hybrid Equivalence (SSE-D-06)

### 5.1 Two-Layer Equivalence

Candidate equivalence is determined by a deterministic hybrid method:

1. **Structural pre-bucket** (fast, deterministic):
   - Descriptor hash
   - Parameter family membership
   - AST-hash subset
   - Groups candidates into structural buckets

2. **Behavioral nearest-rival audit** (within buckets):
   - Compare performance profiles of structurally-similar candidates
   - Detect functional equivalence despite structural differences
   - Deterministic: thresholds are part of the equivalence definition

### 5.2 Constraints

- **No LLM judge** — equivalence must be fully deterministic
- **Versioned determinism** — thresholds are versioned with the equivalence
  definition; changing thresholds = new equivalence version
- **Thresholds and invalidation** — exact values deferred to downstream topics
  (008: interface, 013: semantics, 017: consumption)

**Trace**: SSE-D-06 → `debate/018-search-space-expansion/final-resolution.md` Decision 5

---

## Traceability

| Section | Issue ID | Source |
|---------|----------|--------|
| §1.1-1.2 Hard Rules + Modes | SSE-D-02 | `debate/018-search-space-expansion/final-resolution.md` Decision 2 |
| §1.3 Cold-Start | SSE-D-03 | `debate/018-search-space-expansion/final-resolution.md` Decision 2 |
| §2.1 Topology | SSE-D-05 | `debate/018-search-space-expansion/final-resolution.md` Decision 4 |
| §2.2-2.3 Inventory | SSE-D-05 | `debate/018-search-space-expansion/final-resolution.md` Decision 4 (Judgment call) |
| §3 APE v1 | SSE-D-11 | `debate/018-search-space-expansion/final-resolution.md` Decision 10 |
| §4 Domain-Seed | SSE-D-10 | `debate/018-search-space-expansion/final-resolution.md` Decision 9 |
| §5 Equivalence | SSE-D-06 | `debate/018-search-space-expansion/final-resolution.md` Decision 5 |
