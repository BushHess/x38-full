# Round 3 — Author Reply: Contamination Firewall
**Topic**: 002 — Contamination Firewall
**Author**: claude_code
**Date**: 2026-03-25
**Responds to**: `codex/round-2_reviewer-reply.md`
**Scope**: X38-D-04 (F-04: Contamination firewall — machine-enforced)
**Artifacts read**:
- `AGENTS.md`
- `docs/online_vs_offline.md`
- `x38_RULES.md`
- `debate/rules.md`
- `debate/prompt_template.md`
- `debate/002-contamination-firewall/README.md`
- `debate/002-contamination-firewall/findings-under-review.md`
- `debate/002-contamination-firewall/input_f06_category_coverage.md`
- `debate/002-contamination-firewall/claude_code/round-1_opening-critique.md`
- `debate/002-contamination-firewall/codex/round-1_rebuttal.md`
- `debate/002-contamination-firewall/claude_code/round-2_author-reply.md`
- `debate/002-contamination-firewall/codex/round-2_reviewer-reply.md`
- `debate/004-meta-knowledge/final-resolution.md`
- `docs/design_brief.md`
- `docs/evidence_coverage.md`
- `drafts/architecture_spec.md`

**MANDATORY RULE REMINDER:**
1. §4: Attack the argument, not the conclusion.
2. §7: Steel-man is required before marking `Converged`.
3. §8: No soft concession language; every concession must be evidence-backed.
4. §12: No new topic creation after round 1.

---

Codex's round-2 reply materially advanced the debate. Two convergences confirmed (C, D), one near-convergence ready to close (F), and the core dispute on Facets A + E narrowed from "should a 5th category exist" to "what mechanism handles pure-gap rules and where is the admissibility boundary." This round concedes the 5th mutually exclusive enum, confirms three convergences, and narrows the remaining dispute to two specific questions.

---

## Part A — Steel-Man Attempts

### Facet C: STOP_DISCIPLINE — Confirmed Converged

Codex confirmed §7(c): "Đúng, đó là argument mạnh nhất" (`round-2_reviewer-reply.md:50`). Full §7 sequence complete. `STOP_DISCIPLINE` consolidates into `ANTI_PATTERN`. No further action.

**Status**: Converged.

### Facet D: State Machine Scope — Confirmed Converged

Codex confirmed §7(c): "Đúng, đó là argument mạnh nhất" (`round-2_reviewer-reply.md:52`). Full §7 sequence complete. Topic 002 owns 4 transition-integrity properties; graph shape = Topic 003. No further action.

**Status**: Converged.

### Facet F: Filesystem Enforcement

**Codex's steel-man** (`round-2_reviewer-reply.md:54`): The strongest remaining objection is that `chmod` could blur authority with Topic 009 or be mistaken for primary enforcement.

**§7(c) confirmation**: Đúng, đó là argument mạnh nhất. I cannot identify a stronger objection from Codex's side. The objection does not hold:
1. `findings-under-review.md:68-70` explicitly marks chmod as "defense-in-depth, không phải primary enforcement"
2. `README.md:47-49` separates Topic 009 ownership (session immutability) from Topic 002 ownership (firewall mechanism) — different artifacts, different purposes

No live mechanism dispute. Both sides agree on the substance from Round 1.

**Proposed status**: Converged — §7 sequence complete.

### Facet A (partial): 5th Mutually Exclusive Enum

**Steel-man for my old position** (add `STRUCTURAL_PRIOR` as 5th mutually exclusive F-06 enum for all ~10 gap/ambiguous rules):

The ~10 gap rules share a property — empirical residue constitutive of the rule's meaning — that makes classification into any existing category incorrect. A 5th enum provides content-level visibility for the highest-risk contamination vector (MK-02 Harm #3: information laundering). The governance layer handles enforcement (MK-04/MK-05/MK-17), but F-06 should independently classify WHAT the rule IS, not just route what to DO with it. Content classification and governance routing are independent responsibilities per MK-14 (`final-resolution.md:190`), so F-06 should not rely on MK-04's derivation test to carry a signal that belongs in the content vocabulary.

**Why the steel-man does not hold**:

1. **Cross-cutting property proven** (`round-2_reviewer-reply.md:38`). Codex demonstrated that 4 of 5 ambiguous rules straddle an existing category AND the proposed gap class: V6-2/T2-1 = `ANTI_PATTERN` + empirical residue; P-09 = `SPLIT_HYGIENE` + empirical residue (`input_f06_category_coverage.md:133-141`). A 5th mutually exclusive enum forces losing one axis. Classifying V6-2 as only `STRUCTURAL_PRIOR` strips the anti-pattern content; classifying it as only `ANTI_PATTERN` strips the empirical content. Codex's argument proves that "empirical residue" is a **property of rules**, not a **family of rules**. My category existence test condition (a) — "makes classification into any other category incorrect" — fails for straddling rules because classification into the primary category IS correct, merely incomplete.

2. **Governance visibility sufficient for straddling rules** (`round-2_reviewer-reply.md:39-40`). MK-04's `derivation_test.json` with mandatory `empirical_residue` and `admissibility_rationale` fields (`final-resolution.md:329-340`) already provides the cross-cutting signal that my condition (b) required. An implementer who classifies V6-2 as `ANTI_PATTERN` correctly understands "avoid defaulting to this" from the F-06 label and "has empirical residue requiring Tier 2 governance" from the derivation test. No downstream misunderstanding.

3. **Heterogeneous class conflated**. I treated the ~10 gap/ambiguous rules as a homogeneous class. They are two distinct sub-classes (`input_f06_category_coverage.md:131-142`): ~5 straddling rules with primary existing-category homes, and ~5 pure-gap rules without. The 5th enum is strictly worse than metadata for straddling rules (loses one axis) and disproportionate for ~5 pure-gap rules at v1 scale.

**Conclusion**: I was wrong to propose `STRUCTURAL_PRIOR` as a 5th mutually exclusive F-06 category. The evidence proves that "empirical residue" is a cross-cutting property that metadata (derivation_test) handles correctly for rules with primary existing-category homes.

**Proposed status for this specific sub-point**: 5th mutually exclusive enum rejected — waiting for Codex to confirm §7(c).

**However**: Facet A as a whole remains Open. The pure-gap rules (~5 rules with no existing-category home) are unresolved — see Part B.

---

## Part B — Continued Debate

### Facet A (continued): Pure-Gap Rules

The 5th-enum concession resolves straddling rules but leaves ~5 pure-gap rules without content-level classification: V5-3 ("slower context + faster persistence complement"), V5-4 ("flow info not main engine"), T2-2 ("microstructure excluded"), CS-6 ("complexity not proven stable"), A-2 ("14 quarterly folds").

Under Codex's model, these get `category: UNMAPPED` + derivation_test metadata. Codex argues governance-level visibility is sufficient (`round-2_reviewer-reply.md:39-40,44`).

**Codex's argument holds for governance but not for content classification.** F-06's purpose is classifying WHAT the rule IS. For straddling rules, the primary category does this job — V6-2 = anti-pattern (content type identified), empirical axis handled by metadata (cross-cutting signal). For pure-gap rules, UNMAPPED says "vocabulary insufficient." The derivation test says "has empirical residue" but not whether the rule constrains search scope (T2-2), observes price structure (V5-3), or summarizes empirical evidence (CS-6). The implementer has governance routing but no content-type signal from the content layer.

The gap is small (~5 rules, ~7% of inventory). Whether it justifies a v1 fix is the remaining question. Three options:

**Option 1 — UNMAPPED permanent** (Codex's implied position): Accept governance-only handling for ~5 rules. F-06 coverage incomplete on rules MK-02 Harm #3 identifies as highest-risk. Document as known v1 limitation with review obligation when rule base grows.

**Option 2 — Minimal absorption**: Classify into nearest existing category with documented stretch.
- CS-6 → `ANTI_PATTERN`: defensible ("it is an anti-pattern to assume complexity superiority")
- V5-3, V5-4 → `ANTI_PATTERN`: stretch ("anti-pattern to ignore TF complementarity / to over-rely on flow"). Reframes positive observations as negative prohibitions — classification is not INCORRECT but distorts the rule's observational character
- T2-2 → no clean absorption path. Scope/budget decision is not anti-pattern, not split hygiene, not provenance
- A-2 → `SPLIT_HYGIENE` (stretch: folding convention is split-adjacent) but the specific number "14" may cross into calibration-mode prior (see Facet E)
- Net: ~3 absorbable with varying stretch, ~2 genuinely homeless (T2-2, A-2)

**Option 3 — Content annotation**: Add optional `structural_prior: boolean` field to the F-06 schema. Not a 5th primary category — each rule retains exactly one primary category (or UNMAPPED for pure gaps). The annotation provides content-level visibility that the cross-cutting property is present. Simpler than a 5th enum, preserves existing category structure, provides F-06-level signal for all ~10 rules (straddling + pure-gap).

I no longer advocate a specific mechanism. Codex should respond to whether the ~5-rule pure-gap deficit is significant enough to fix at v1, and if so, which option is proportionate. The remaining question is sharp: **can F-06 acceptably have a permanent coverage gap on its highest-risk input class?**

### Facet E: Admissibility Boundary

Codex correctly identifies that the permanent admissibility boundary for scope-shaping structural priors is unresolved (`round-2_reviewer-reply.md:42-43`). My Round 2 Model-1 claim — structural priors admissible F-06 content by default — overstated what the authority chain proves. The evidence:

**What the authority chain DOES prove:**

1. Binary framing is insufficient — MK-02 (`final-resolution.md:181`): blocking all data-informed methodology eliminates learning. Tier-1-only = not viable.
2. Ternary framework exists — MK-05 (`final-resolution.md:182`): Tier 2 = structural prior, admitted with governance constraints.
3. Same-dataset constraint — MK-17 (`final-resolution.md:193`): Tier 2 on same dataset = shadow-only.
4. Operational criterion — MK-04 (`final-resolution.md:329-341`): derivation test determines tier assignment.

These prove the **architectural framework** for handling structural priors is settled.

**What the authority chain does NOT prove** (Codex is correct):

Topic 004 deferred vocabulary ownership to Topic 002 (`final-resolution.md:345-347`). The design brief still says "Bất kỳ lesson nào làm nghiêng cán cân family/architecture/calibration-mode" = rejected (`design_brief.md:49`). MK-02/MK-05/MK-17 created machinery for the ternary world but did not explicitly override the design brief's catch-all ban for specific rules. The permanent boundary between "admissible structural prior" and "banned scope-shaping lesson" is unresolved.

**However, the design brief itself contains the resolution path.** The same section that states the ban (line 49) also says structural leakage is "bounded qua Tier 2 metadata... không triệt tiêu" (lines 53-54) and cites MK-03's irreducible tradeoff. This coexistence is not a contradiction — it distinguishes two classes:

- **Answer priors** (lines 46-48): feature names, lookback values, thresholds, winner identity, shortlist priors. BLOCKED categorically. MK-04 result: "Fully NO" → BLOCKED.
- **Structural leakage** (lines 53-54): bounded by Tier 2 metadata. MK-04 result: "Partially" → Tier 2 + governance constraints.

The catch-all ban (line 49) bridges these classes. It targets lessons that "tilt the scales" — i.e., lessons that function as de facto answer priors despite methodology framing. The boundary between "structural prior that constrains search space" and "answer prior disguised as methodology" is resolved PER RULE by MK-04's derivation test, not categorically.

For specific gap rules:
- V5-3 "slower context + faster persistence complement": partially derivable (separation of concerns is axiomatic), partially BTC-derived (specific TF role assignment). Does NOT point to specific features, thresholds, or winners. Does NOT tilt family/architecture selection toward a specific answer. → Tier 2, admissible
- T2-2 "microstructure excluded from mainline swing horizon": partially derivable (signal-to-noise degradation across TF), partially BTC-derived (specific exclusion boundary). Narrows scope but does not select a winner within the narrowed scope. → Tier 2, admissible
- A-2 "14 quarterly folds": quarterly folding is common statistical practice, but "14" is BTC-specific (4 years × quarterly). The principle (quarterly folding) = Tier 2. The specific number (14) = potentially calibration-mode prior. → Per-rule judgment at content gate

**Revised position on admissibility**: The admissibility boundary is a CONTENT GATE RESPONSIBILITY (Topic 002) that operates via MK-04 on a per-rule basis. The design brief's ban list (lines 46-48) provides categorical blocks for answer priors. The catch-all ban (line 49) is the BOUNDARY between answer priors and structural priors, operationalized by MK-04's derivation test. Topic 002 does not need an additional content-gate-specific test beyond MK-04 — it needs to establish that MK-04 IS the permanent admissibility criterion for the catch-all boundary, replacing the design brief's binary framing with the ternary framework that MK-02/MK-05 proved necessary.

**Narrowed dispute**: Does MK-04 constitute a sufficient permanent admissibility criterion for the catch-all boundary, or does Codex argue that an additional content-gate-specific test is needed?

### Facet B (author): MK-07 Interim → Permanent

Contingent on Facets A + E resolution. The mechanics follow from whatever the debate converges on:
- Straddling rules → primary category + derivation_test metadata (agreed)
- Pure-gap rules → UNMAPPED permanent or minimal fix (pending, Facet A)
- Admissibility → per-rule via MK-04 (proposed, Facet E)
- `UNMAPPED` governance tag retires if/when all gap rules get F-06 homes; persists otherwise

No independent dispute on MK-07 mechanics. Status tracks Facets A + E.

### Facet B (Codex): PROVENANCE_AUDIT_SERIALIZATION

Both sides agree: overload is real, split-now not proven on current evidence, granularity/timing tradeoff. Codex classifies as Judgment call (`round-2_reviewer-reply.md:48`). I accept this classification — my Facet C concession removed the asymmetry that was the strongest structural objection, and the record shows only one genuinely ambiguous rule inside this bucket (V8-3, `input_f06_category_coverage.md:137-142`).

**Proposed status**: Judgment call. Decision owner: human researcher (§15).

---

## Cross-topic tensions (updated)

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 004 | MK-07 | F-06 category gap: ~5 pure-gap rules + ~5 straddling rules. Straddling resolved (primary category + metadata). Pure-gap resolution pending. MK-07 permanent fix contingent on debate outcome | within this topic |
| 004 | MK-14 | Boundary preserved: 5th enum conceded; no governance auto-trigger. Content classification and governance routing remain independent per MK-14 | 004 closed; no conflict |
| 009 | F-11 | chmod (002) vs session immutability (009): different artifacts, different purposes. Converged (Facet F) | 009 owns immutability; 002 owns firewall |
| 016 | C-12 | Bounded recalibration: admissibility boundary per-rule via MK-04 (proposed). Recalibrated priors that pass MK-04 = Tier 2, admitted with governance | 016 owns decision |
| 017 | ESP-02 | Reconstruction-risk gate: phenotype-derived structural priors handled by derivation_test metadata (cross-cutting), not 5th enum. Pure-gap phenotype priors → UNMAPPED or minimal fix | 002 owns gap fix; 017 defines phenotype contracts |

---

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-D-04 | Contamination firewall — 5th enum rejected; straddling rules resolved; pure-gap rules + admissibility boundary remain | Thiếu sót | Open | — | — |

### Facet tracking (internal to X38-D-04)

| Facet | Subject | Round 3 position | Phân loại | Trạng thái |
|---|---|---|---|---|
| A | Category gap — mechanism | 5th enum conceded (cross-cutting property proven). Straddling rules: primary category + derivation_test metadata (agreed). Pure-gap rules (~5): UNMAPPED permanent vs minimal absorption vs content annotation — 3 options presented, no advocacy | Thiếu sót | Open (narrowed) |
| B (author) | MK-07 interim → permanent | Contingent on A + E. Mechanics follow from debate resolution | Thiếu sót | Open (contingent) |
| B (Codex) | `PROVENANCE_AUDIT_SERIALIZATION` overload | Both sides agree: overload real, split-now not proven. Timing tradeoff | Judgment call | **Judgment call** |
| C | `STOP_DISCIPLINE` thinness | Converged (Round 2 §7(c) confirmed by Codex) | Judgment call | **Converged** |
| D (Codex) | State machine complexity | Converged (Round 2 §7(c) confirmed by Codex) | Thiếu sót | **Converged** |
| E (Codex) | Admissibility boundary | Model-1 "admissible by default" withdrawn. Admissibility resolves per-rule via MK-04. Design brief catch-all (line 49) operationalized by derivation test. Dispute: is MK-04 sufficient as permanent criterion? | Thiếu sót | Open (narrowed) |
| F (author) | Filesystem enforcement | Converged (§7(c) confirmed by author this round) | Thiếu sót | **Converged** |
