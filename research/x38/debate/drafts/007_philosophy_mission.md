# Draft Spec Sections — Topic 007: Philosophy & Mission Claims

**Source**: `debate/007-philosophy-mission/final-resolution.md`
**Closed**: 2026-03-23
**Status**: Draft sections ready for integration into target specs

These sections are ready to be incorporated when their target specs are drafted
(after dependent topics also close). Each section traces to the originating issue
and evidence.

---

## For `architecture_spec.md`

### Section: Philosophy Invariant (from X38-D-01)

**V1 invariant**: The framework inherits research methodology from V4-V8, not
answers. It promises to find the strongest candidate WITHIN the declared search
space, or honestly conclude `NO_ROBUST_IMPROVEMENT`.

**Constraints**:
- `NO_ROBUST_IMPROVEMENT` is a valid verdict equal in status to
  `INTERNAL_ROBUST_CANDIDATE` — not a failure mode.
- "Better than online" means: broader search, reproducible, less contamination,
  better audit. NOT "always produces a better algorithm."
- F-01 is not self-executing — it requires operationalization through the
  contamination firewall (see Topic 002, C-10).

**Evidence**: `docs/design_brief.md:24-30`, `PLAN.md:209-217`,
`RESEARCH_PROMPT_V6.md:7-13` [extra-archive].

### Section: 3-Tier Claim Model (from X38-D-20)

**V1 invariant**: Three semantic tiers:

| Tier | Scope | Verdict-bearing | Outputs |
|------|-------|-----------------|---------|
| **Mission** | Charter framing | No | Named in prose only |
| **Campaign** | Strongest leader in declared search space | Yes | `INTERNAL_ROBUST_CANDIDATE`, `NO_ROBUST_IMPROVEMENT` |
| **Certification** | Independent scientific validation | Yes | `CLEAN_OOS_CONFIRMED`, `CLEAN_OOS_INCONCLUSIVE`, `CLEAN_OOS_FAIL` |

**Constraints**:
- Mission appears in prose as ongoing aspiration, never in verdict tables.
- Campaign and Certification are the only two verdict-bearing tiers.
- Campaign output is valid evidence but is not certification.

**Evidence**: `PLAN.md:7-11` (charter), `PLAN.md:35-37, 51-60, 454-478`
(verdict-bearing states), `PROMPT_FOR_V[n]_CLEAN_OOS_V2[en].md:76-81`
[extra-archive] (clean OOS distinction).

### Section: Phase 1 Evidence Taxonomy (from X38-D-22)

**V1 invariant**: Three evidence types, organized by source and claim ceiling:

1. **Coverage/process** (same-archive): Exhaustive scan confirms or contradicts
   prior family-level results.
2. **Deterministic convergence** (same-archive): N procedurally-blind sessions
   produce the same leader.
3. **Clean adjudication** (new data): Requires appended data not present in the
   training/development archive.

Phase 1 on exhausted archives produces types 1 and 2 only. Type 3 requires
Phase 2 (appended data).

**Semantic rule**: If same-archive search (of either type) contradicts the
historical lineage, the artifact MUST surface that contradiction explicitly
and keep it below certification tier.

**Not frozen**: Sub-type taxonomy within same-archive categories. Consuming
topics (001 campaign-model, 010 clean-oos-certification) define routing,
escalation, and judgment mechanics.

**Evidence**: `findings-under-review.md:118-147`, `PLAN.md:497-510`,
`CONVERGENCE_STATUS_V3.md:126-145` [extra-archive].

### Section: Regime-Aware Policy Structure (from X38-D-25)

**V1 invariant**: A single frozen policy object may contain evidence-backed
internal conditional logic.

**Allowed**:
- Internal conditional branches with paired ablation evidence
  (e.g., D1 EMA regime filter in E5_ema21D1)

**Forbidden**:
- Per-regime parameter tables (separate parameter sets for different regimes)
- External framework-provided regime classifiers
- Post-freeze switching between regime-specific sub-strategies

**Evidence**: `RESEARCH_PROMPT_V8.md:469-477` [extra-archive] (V8 ban scope),
`RESEARCH_PROMPT_V8.md:312-331` [extra-archive] (layered structures allowed),
`DEPLOYMENT_CHECKLIST.md:4-18` [extra-archive] (E5_ema21D1 regime filter),
`MONITOR_V2_VALIDATION_REPORT.md:89-98` [extra-archive] (filter value: Sharpe
1.4545 vs 1.0912 without).

---

## For `meta_spec.md`

### Section: Philosophy Statement (from X38-D-01)

Cross-reference to `architecture_spec.md` § Philosophy Invariant. The philosophy
constrains meta-knowledge governance: meta-rules must enable methodology
inheritance, not answer inheritance. F-01 depends on the contamination firewall
(C-10) for operationalization.

---

## For `protocol_spec.md`

### Section: Evidence Type Routing (from X38-D-22)

Cross-reference to `architecture_spec.md` § Phase 1 Evidence Taxonomy. Protocol
stages must distinguish evidence types 1-3 and enforce the semantic rule
(explicit surfacing of lineage contradiction, below-certification ceiling).
Routing mechanics to be defined when topics 001 and 010 close.

### Section: Regime-Aware Ablation (from X38-D-25)

Cross-reference to `architecture_spec.md` § Regime-Aware Policy Structure.
Protocol must include ablation gate for regime-aware structures. Specific
thresholds and test design to be defined when topic 003 closes.
