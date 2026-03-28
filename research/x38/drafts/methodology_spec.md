# Methodology Spec — Draft

**Status**: DRAFT (seeded from Topic 013 closure)
**Last updated**: 2026-03-28
**Dependencies**: 013(CLOSED)
**Publishable when**: ALL dependencies CLOSED (currently only 013 contributes; more sections expected from future topic closures)

---

## 1. Convergence Algorithm (Topic 013)

> Source: `debate/013-convergence-analysis/final-resolution.md` Decision 1 (X38-CA-01)

### 1.1 Measurement Law

Kendall's W as convergence metric. W measures ordinal agreement across N sessions
ranking K candidates.

**Null distribution derivation**: Procedure to compute tau_low (noise floor) and
tau_high (near-identical threshold), parametric on K. Category boundaries adapt
automatically to the number of items being ranked.

**Two-mechanism architecture**:
- **Ordinal agreement** (W-based): measures rank concordance across sessions.
  Produces convergence categories at levels 1-3 (NOT/PARTIALLY/FULLY_CONVERGED).
- **Cardinal equivalence** (SSE-04-THR): behavioral equivalence via paired-return
  correlation (rho > 0.95). Structural hash pre-bucketing. Operates at level 4,
  complementing ordinal agreement for cross-bucket functional equivalence.

### 1.2 Multi-Level Categories

| Category | Meaning | Winner-eligibility | Next action |
|----------|---------|-------------------|-------------|
| `NOT_CONVERGED` | No winner-stability signal | No | Continue research or HANDOFF |
| `PARTIALLY_CONVERGED` | Useful agreement signal | No | Narrowing, same-data HANDOFF, continued research |
| `FULLY_CONVERGED` | Convergence-side prerequisite for winner-recognition | Yes (necessary, not sufficient) | Additional quality preconditions from 010/017 |

**Key invariant**: `PARTIALLY_CONVERGED` does NOT open Clean OOS progression.
Only `FULLY_CONVERGED` satisfies the convergence-side prerequisite for Topic 010's
`(winner exists)` predicate.

**Asset-agnostic property**: Kendall's W is inherently asset-agnostic (ordinal metric,
independent of number of families/candidates). Thresholds are percentile-based via
null distribution, adapting to K automatically. No asset-specific calibration required.

### 1.3 Convergence-Side Prerequisite Semantics

`FULLY_CONVERGED` is the convergence-side prerequisite for `(winner exists)` in the
sense of Topic 010's Clean OOS auto-trigger. This does NOT imply:
- That `FULLY_CONVERGED` alone is sufficient for winner declaration
- That Topic 013 owns the full winner-recognition routing matrix

Full routing (what action follows each convergence state) is cross-topic integration
between Topics 001, 003, 010, and 013.

### 1.4 Exported Outputs

Topic 013 exports:
- **Convergence-state**: `NOT_CONVERGED` | `PARTIALLY_CONVERGED` | `FULLY_CONVERGED`
- **Stall signal**: boolean, consumed by stop-law (section 2)

Consumed by: Topic 003 (pipeline stop logic), Topic 010 (winner-exists predicate),
Topic 001 (HANDOFF triggers).

**Trace**: X38-CA-01 -> `debate/013-convergence-analysis/final-resolution.md` Decision 1

---

## 2. Stop Conditions (Topic 013)

> Source: `debate/013-convergence-analysis/final-resolution.md` Decision 2 (X38-CA-02)

### 2.1 Stop-Law Structure

**Stall detection**:
```
|delta_W_N| < max(epsilon_noise, epsilon_cost) for M consecutive sessions
```
where `delta_W_N = W(1..N+1) - W(1..N)`.

- delta_W observations begin at session 3 (first marginal-gain observation requires
  at least 3 sessions to compute two W values).
- Cross-campaign ceiling bounds same-dataset repetition.

### 2.2 Bootstrap Defaults (v1)

All defaults are explicitly **provisional** / **human-overridable** /
**recalibration-required** after first genuine offline campaign evidence.

| Constant | Value | Provenance tier | Rationale |
|----------|-------|----------------|-----------|
| `S_min` | 3 | Structure-implied | First delta_W at session 3. Not tunable. |
| `epsilon_cost = epsilon_noise` | (equal) | V1 simplifying default | Internalizes stop-law within 013. |
| `M` | 2 | Early-stop convention | M=2 for earlier detection. M=3 also compatible. |
| `S_max` | 5 | Weak paradigm heuristic | From V4->V8 session count. Directional. |
| `same_data_ceiling` | 3 | Weak cross-archive heuristic | Weakest provenance. |

### 2.3 Provenance Model (5 tiers)

Constants are ranked by evidential strength. This model ensures consumers know
exactly how much to trust each default.

| Tier | Description | Recalibration expectation |
|------|-------------|--------------------------|
| 1. Structure-implied | Mechanically derived from stop-law definition | Stable unless stop-law changes |
| 2. V1 simplifying default | Chosen for v1 simplicity, not calibrated | Likely refined in v2 |
| 3. Early-stop convention | Compatible but not required; preference | May adjust after first campaign |
| 4. Weak paradigm heuristic | Directional from V4->V8 | Recalibrate after first offline campaign |
| 5. Weak cross-archive heuristic | Unit/archive mapping unclear | Recalibrate with high priority |

### 2.4 Coupling Constraint

```
M <= (S_max - S_min + 1)
```

At current values: M=2 <= (5 - 3 + 1) = 3. Coupling is not active.
If S_max is revised upward after calibration, M must be re-evaluated.

### 2.5 Cross-Topic Interaction

If Topic 017 closes a coverage floor obligation, that obligation may delay the stop
suggestion (coverage floor not met -> extend campaign even if convergence stall
detected). Recorded as 013x017 cross-topic tension; no action required now.

**Trace**: X38-CA-02 -> `debate/013-convergence-analysis/final-resolution.md` Decision 2

---

## Traceability

| Section | Issue ID | Source |
|---------|----------|--------|
| 1.1 Measurement Law | X38-CA-01 | `debate/013-convergence-analysis/final-resolution.md` Decision 1 |
| 1.2 Multi-Level Categories | X38-CA-01 | `debate/013-convergence-analysis/final-resolution.md` Decision 1 |
| 1.3 Prerequisite Semantics | X38-CA-01 | `debate/013-convergence-analysis/final-resolution.md` Decision 1 |
| 1.4 Exported Outputs | X38-CA-01 | `debate/013-convergence-analysis/final-resolution.md` Decision 1 |
| 2.1 Stop-Law Structure | X38-CA-02 | `debate/013-convergence-analysis/final-resolution.md` Decision 2 |
| 2.2 Bootstrap Defaults | X38-CA-02 | `debate/013-convergence-analysis/final-resolution.md` Decision 2 |
| 2.3 Provenance Model | X38-CA-02 | `debate/013-convergence-analysis/final-resolution.md` Decision 2 |
| 2.4 Coupling Constraint | X38-CA-02 | `debate/013-convergence-analysis/final-resolution.md` Decision 2 |
| 2.5 Cross-Topic Interaction | X38-CA-02 | `debate/013-convergence-analysis/final-resolution.md` Decision 2 |
