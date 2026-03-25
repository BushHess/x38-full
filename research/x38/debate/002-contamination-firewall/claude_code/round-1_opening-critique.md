# Round 1 — Opening Critique: Contamination Firewall

**Topic**: 002-contamination-firewall
**Author**: claude_code
**Date**: 2026-03-25
**Scope**: X38-D-04 (F-04: Contamination firewall — machine-enforced)
**Input documents**:
- `debate/rules.md` — debate governance
- `x38_RULES.md` — project rules + authority order
- `AGENTS.md` — agent context
- `docs/online_vs_offline.md` — paradigm distinction (mandatory per §25)
- `docs/design_brief.md` — authoritative design input (§3.1 Contamination Firewall)
- `docs/evidence_coverage.md` — evidence tracker (§2.5 Contamination Log, §2.9 V5→V6 provenance)
- `debate/prompt_template.md` — round format (Prompt A)
- `debate/002-contamination-firewall/README.md` — topic scope, dependencies, cross-topic tensions
- `debate/002-contamination-firewall/findings-under-review.md` — F-04 (Open)
- `debate/002-contamination-firewall/input_f06_category_coverage.md` — pre-debate input (~75 rules mapped, 4 sub-findings A-D)
- `debate/004-meta-knowledge/final-resolution.md` — MK-07 amended interim rule, MK-14 boundary contract, MK-08 lifecycle, V1 frozen invariants (D1/D4/D5/D7/D8/D9)
- `drafts/architecture_spec.md` — current draft (§7 stub pending this topic)

---

## Preamble

As architect of the contamination firewall design (`design_brief.md:36-55`), I authored the 3-layer enforcement proposal — typed schema with whitelist categories, state machine with hash-signed transitions, and filesystem read-only as supplementary guardrail. I also conducted the F-06 category coverage investigation (`input_f06_category_coverage.md`) that tested my own design against ~75 actual V4-V8 rules. Per rules.md §5, burden of proof falls on the party proposing change. For the original F-04 design, that burden is mine. For amendments proposed in this critique, that burden is equally mine.

The contamination firewall is Alpha-Lab's highest-stakes subsystem. In the online lineage (V4→V8), contamination accumulated across 8 rounds despite explicit prohibition — CONTAMINATION_LOG_V4.md [extra-archive] documents 1,692 lines of data-derived specifics leaking through honor-based isolation. The core lesson (`evidence_coverage.md:221-223`): text-based isolation demonstrably fails when the enforcer (AI or human) has incentives to interpret rules flexibly. Alpha-Lab is OFFLINE (`online_vs_offline.md` §1): "Governance là *code* tự enforce — filesystem gating, chmod, automated checks." The firewall must be machine-enforced because it IS the machine; there is no external enforcer to trust or distrust.

Scope: This topic owns the ENFORCEMENT MECHANISM — how the firewall validates, classifies, and gates meta-knowledge content. Per MK-14 boundary contract (Topic 004 converged, `final-resolution.md:190`): Topic 002 owns the content gate (`ADMISSIBLE/BLOCKED`); Topic 004 owns the lifecycle gate. This topic does NOT own session immutability (Topic 009), bounded recalibration policy (Topic 016), or epistemic search policy / phenotype contracts (Topic 017). The enforcement architecture must accommodate those topics' decisions without pre-empting them.

F-04 is a single finding but encompasses the full enforcement mechanism. The MK-07 investigation (`input_f06_category_coverage.md`) expanded the original open questions with empirical data: ~75 rules mapped, ~60 clean fit (80%), ~10 gap (13%), ~5 ambiguous (7%). I treat the 4 sub-findings (A through D) as facets of F-04 rather than separate issues, per the topic README debate plan. I also address two additional facets (E, F) for the state machine and filesystem enforcement layers that were among F-04's original open questions.

---

## X38-D-04: Contamination Firewall — ACCEPT with amendments

### Position

The 3-layer architecture is sound: typed schema as primary content gate, state machine as transition integrity enforcer, filesystem chmod as defense-in-depth. The enforcement model correctly mirrors offline paradigm needs — code self-enforces rather than relying on AI/human discipline (`online_vs_offline.md` §2: "Meta-knowledge leakage: Online → prompt instruction; Offline → typed schema + whitelist category + state machine").

**Key argument**: The enforcement architecture is correct, but the whitelist vocabulary is incomplete. The F-06 investigation proved empirically that ~13% of actual V4-V8 rules have no category home. These are the Tier 2 structural priors that MK-02 Harm #3 (Topic 004 converged, `findings-under-review.md:114-116` [extra-archive from 004]) identified as the highest-risk contamination vector: "data-specific lessons become universal-looking rules. A new AI cannot distinguish genuine methodology from data-derived heuristics." A firewall that cannot correctly classify its highest-risk input class is operationally incomplete.

**Evidence**:
- `input_f06_category_coverage.md` §5.1: 10 specific gap rules, all Tier 2 structural priors
- `input_f06_category_coverage.md` §8: Root cause = binary design (ALLOWED/BLOCKED) in a ternary world
- `004-meta-knowledge/final-resolution.md:360-364`: MK-07 amendment acknowledges gap, introduces `UNMAPPED` tag as interim
- `design_brief.md:51-55`: Original design already hedged ("bounded qua Tier 2 metadata... không triệt tiêu")

**However**: The gap's existence is proven; its optimal solution is not. Three resolution paths exist, and this critique cannot pre-select the winner without reviewer challenge:
1. Add 5th category (`STRUCTURAL_PRIOR`) — explicit handling for mixed-content rules
2. Redefine existing categories — absorb gap rules into broadened definitions
3. Accept `UNMAPPED` as permanent governance path — no new category, perpetual human routing

I argue for Path 1 below. The reviewer should pressure-test Paths 2 and 3.

**Proposed amendment (summary)**: Add `STRUCTURAL_PRIOR` as 5th whitelist category, resolving MK-07 permanently. Keep `STOP_DISCIPLINE` despite thin rule count. Defer `PROVENANCE_AUDIT_SERIALIZATION` split to v2+. Confirm state machine and filesystem enforcement as designed.

### Classification: Thiếu sót

The enforcement architecture is correct. The whitelist vocabulary has a proven gap affecting the firewall's highest-risk input class. This is an omission in the design, not a wrong design choice.

---

### Facet A: Category Gap for Tier 2 Priors — ACCEPT + ADD STRUCTURAL_PRIOR

The 4 F-06 categories were designed for a binary enforcement world: ALLOWED (methodology that any researcher could derive independently) vs BLOCKED (data-derived specifics caught by schema validation). MK-02 Harm #3 (Topic 004 converged) proved the world is ternary: there exists a class of empirical lessons elevated to methodology — rules partially derivable from first principles and partially informed by data experience.

**Key argument**: A 5th category is superior to redefining existing categories for three reasons:

1. **Discriminating power**: Stuffing V5-3 ("slower directional context + faster state persistence complement") into `ANTI_PATTERN` destroys the category's meaning. V5-3 is not an anti-pattern — it is an empirical observation about BTC price structure. Similarly, V6-2/T2-1 ("layering is hypothesis, not default") has an anti-pattern reading (Occam's razor) but also data-derived content (V4-V5 evidence that multi-layer didn't help). Force-fitting conflates methodology with empiricism.
   Evidence: `input_f06_category_coverage.md:125` — "stretching ANTI_PATTERN to fit them destroys discriminating power."

2. **Differential enforcement**: `STRUCTURAL_PRIOR` rules require mandatory Tier 2 + SHADOW + provenance metadata (per MK-05 converged, MK-17 resolved). The other 4 categories can contain Tier 1 axioms that need no such constraints. A category that triggers different enforcement actions is architecturally distinct — not just a labeling convenience.

3. **MK-02 Harm #3 alignment**: The most dangerous contamination vector — information laundering — maps exactly to this category. Making it first-class gives the firewall explicit handling for its highest-risk input, rather than routing through a generic `UNMAPPED` path that carries no enforcement semantics.

**However**: A 5th category risks becoming a dumping ground. If `STRUCTURAL_PRIOR` is defined too broadly, implementers may route genuine methodology rules into it to avoid classification effort — the exact problem it is designed to solve. The classification test must be sharp enough to prevent misuse.

**Proposed amendment**:
- Add `STRUCTURAL_PRIOR` to the typed schema `category` enum
- Classification gate: MK-04 derivation test (`final-resolution.md:329-341`) must show `empirical_residue ≠ empty`. Rules with zero empirical residue belong in the 4 methodology categories.
- Auto-constraints: `tier: 2` (minimum), `shadow: true` on same-dataset (MK-17), `provenance: required`
- Negative test: "Could a researcher with NO access to this project's data independently derive this complete rule?" Fully YES → methodology category. Partially → `STRUCTURAL_PRIOR`. Fully NO → BLOCKED (answer prior, not a transferable rule)
- Positive test (from `input_f06_category_coverage.md` §5.3): rule must share ALL three common properties — empirical content, methodology disguise, not blockable (should be admitted with governance, not rejected)

### Classification: Thiếu sót

---

### Facet B: MK-07 Interim Rule Resolution — ACCEPT amended + PERMANENT fix

The amended MK-07 interim rule (`004-meta-knowledge/final-resolution.md:373-392`) correctly distinguishes GAP from AMBIGUITY. If this topic adds `STRUCTURAL_PRIOR`, the gap disappears and the `UNMAPPED` governance tag retires.

**Key argument**: The GAP/AMBIGUITY distinction maps onto two fundamentally different enforcement problems:

- **AMBIGUITY** (rule fits multiple categories): The content IS within F-06 scope; the question is routing. Fail-closed (non-admissible pending human review) is correct — wrong routing could misapply enforcement constraints.

- **GAP** (rule fits no category): Fail-closed was wrong-direction for structural priors. Blocking loses methodology content that the governance system (tier + shadow) was specifically designed to handle safely. The walkthrough in `input_f06_category_coverage.md` §7 demonstrates the failure: implementer encounters V5-3 → no category fits → declares "ambiguous" → non-admissible → human reviews → no category to assign → rule stuck in limbo.

**Evidence**: After adding `STRUCTURAL_PRIOR`, the 10 gap rules from `input_f06_category_coverage.md` §5.1 all map cleanly. The ~5 ambiguous rules (§6) reduce to ~1 genuine ambiguity (V8-3: PROVENANCE vs SPLIT_HYGIENE — both valid, no gap). The `UNMAPPED` tag becomes unnecessary.

**However**: If Alpha-Lab discovers NEW rule classes in future campaigns that don't fit the 5 categories, the gap problem returns. `UNMAPPED`-as-permanent scales to arbitrary future rule classes, while adding categories does not. The counter-argument: `UNMAPPED` carries no enforcement semantics — it says "we don't know what this is," which is not useful for a machine-enforced firewall. If a future rule class genuinely needs different enforcement, a category is correct. If not, it can be absorbed into an existing category.

**Proposed amendment**: Adopt `STRUCTURAL_PRIOR` (Facet A) → MK-07 permanent rule:
- **AMBIGUITY**: fail-closed, human review for routing (unchanged from interim)
- **GAP**: if derivation test shows mixed content → `STRUCTURAL_PRIOR`. If no category fits even after the 5th category → `UNMAPPED` + mandatory human review before next campaign boundary + obligation to evaluate category expansion
- **Constraint**: `UNMAPPED` is a governance tag (Topic 004 territory), not a content category (Topic 002 territory). This separation per MK-14/D7 is preserved — `UNMAPPED` is not added to the F-06 enum, it exists in the lifecycle axis.

### Classification: Thiếu sót

---

### Facet C: STOP_DISCIPLINE Thinness — REJECT consolidation

`STOP_DISCIPLINE` has 3 clean-fit rules (V7-2: same-file iteration limit; V8-5: reserve cannot retroactively promote; CS-8: same-file scientific productivity exhausted). Finding C asks whether consolidation into `ANTI_PATTERN` is warranted.

**Key argument against consolidation**: `STOP_DISCIPLINE` captures a conceptually distinct enforcement concern — "when to halt iteration" — that differs from `ANTI_PATTERN`'s "what approaches to avoid." The distinction matters for Meta-Updater (Pillar 3) design:

- Stop rules constrain the FRAMEWORK's own iteration behavior (when to stop searching, when to freeze, when same-file work is exhausted)
- Anti-patterns constrain the SEARCH's behavior (what algorithms/methods to avoid, what not to try)

V7's contribution (`evidence_coverage.md:286-300`) elevated "methodology iteration is itself a search dimension" to a first-class concept. The V6→V7 changelog introduced session-finality statement and stop conditions specifically because unbounded iteration was destroying evidence quality. The Meta-Updater must respect stop rules as a distinct class constraining ITS OWN behavior — not just the pipeline's search behavior.

**Evidence**: The 3 stop rules share a unique property: they are META-LEVEL constraints on the research process itself, not object-level constraints on the algorithms being researched. V7-2 ("same-file editing is search dimension; freeze + explicit stop") is not "don't do X" (anti-pattern form) — it is "know when to stop doing anything" (stop discipline form). This meta-level character is the discriminating property.

**However**: Enforcement actions are identical for `STOP_DISCIPLINE` and `ANTI_PATTERN` — both are ALLOWED through the firewall, both can be Tier 1 or Tier 2, both have the same content gate treatment. The category distinction exists for classification clarity, not for differential enforcement. If enforcement-action equivalence is the criterion for category merging, the argument for consolidation strengthens significantly.

**Proposed amendment**: Keep `STOP_DISCIPLINE` as a separate category. Thin categories with precise boundaries are preferable to overloaded categories with blurred boundaries (contrast with Facet D). The thin-ness is a signal of category precision, not category weakness. If the rule count remains < 5 after 3+ campaigns, re-evaluate in v2+.

### Classification: Judgment call

Both sides have merit. `STOP_DISCIPLINE` preserves a real conceptual boundary (meta-level vs object-level) but adds marginal classification burden for 3 rules. Consolidation reduces categories but loses the distinction. The reviewer should challenge whether conceptual distinction WITHOUT enforcement-action distinction justifies a separate category.

---

### Facet D: PROVENANCE_AUDIT_SERIALIZATION Overloading — DEFER split to v2+

~25+ rules in one category spanning: data provenance, audit trails, serialization formats, session independence, export manifests, hash verification, freeze protocols, and comparison conventions.

**Key argument for deferral**: At v1 scale (~65 clean-fit rules, ~25 in this category), overloading does not cause classification errors. An implementer can correctly classify "seed frozen before bootstrap" (G-01) as `PROVENANCE_AUDIT_SERIALIZATION` without confusion — the category's breadth doesn't prevent correct placement, it only reduces discriminating power for borderline cases (which are rare within this category — V8-3 is the only ambiguous rule here).

**Evidence**: `input_f06_category_coverage.md` §4 shows PROVENANCE_AUDIT (~23) and ANTI_PATTERN (~23) are equally loaded. If overloading warrants splitting, both categories need it. Splitting one without the other creates asymmetric granularity that favors one enforcement domain over another without principled justification.

**However**: The operational span IS wide. Four distinct enforcement concerns are collapsed:
- **Provenance**: WHERE data/rules came from (independence verification)
- **Audit**: THAT they were reviewed (process compliance)
- **Serialization**: HOW they are stored (format correctness, machine-readability)
- **Protocol governance**: WHEN transitions are allowed (stage gating)

These could require different enforcement actions in v2+ — serialization rules are fully machine-verifiable (format checks, hash matching) while provenance rules may require human judgment (independence claims). Deferring the split means v2+ inherits design debt that is harder to unwind when the rule base is larger.

**Proposed amendment**: Keep as-is for v1. Record v2+ obligation to evaluate split when:
(a) total rule count in `PROVENANCE_AUDIT_SERIALIZATION` exceeds 40, OR
(b) implementers report classification confusion (empirical signal, not prediction), OR
(c) enforcement actions need differentiation (e.g., machine-verifiable vs human-judgment sub-categories)

The split boundary, if needed, should follow enforcement-action alignment, not conceptual grouping.

### Classification: Judgment call

Splitting now adds spec complexity without proven implementation benefit at v1 scale. Deferral risks growing design debt. This is a timing question, not a correctness question.

---

### Facet E: State Machine Enforcement — ACCEPT as designed

The F-04 state machine proposal (`findings-under-review.md:63-66`): stage transitions signed by hash of current artifacts, contamination log readable only after `frozen_spec.json` hash exists, state machine prevents rollback (FROZEN → SCANNING is invalid).

**Key argument**: The state machine is the PRIMARY integrity mechanism. It ensures protocol stages execute in order and artifacts cannot be modified post-transition. This is the offline implementation of what V6 attempted through text instructions — "Admissible inputs lock: only prompt + raw data before freeze" (`evidence_coverage.md:274`). The difference: V6 relied on AI compliance; Alpha-Lab enforces via code.

V1 scope is manageable. Per MK-17 (same-dataset = all empirical priors SHADOW-only) and C6 (converged: "Stage runtime aggressively; freeze governance invariants now"), the v1 state machine needs only the discovery pipeline transitions:

```
PROTOCOL_LOCKED → SCANNING → FROZEN → EVALUATION → VERDICT
```

It does NOT need Meta-Updater state transitions (those are v2+ per MK-09, MK-10). The MK-08 lifecycle state machine (3-axis: `constraint_status` / `semantic_status` / `lifecycle_state`) operates in the meta-knowledge domain, not the pipeline domain — these are orthogonal state machines, not one monolithic graph.

**Evidence**:
- `design_brief.md:64-66`: Hash-signed transitions specification
- `evidence_coverage.md:221-223`: Contamination Log V4 structure — working template of what the firewall must track, currently manual
- V6 provenance response (`evidence_coverage.md:274-275`): Admissible inputs lock — the online rule that Alpha-Lab's state machine automates

**However**: Hash-signed transitions add operational overhead per transition. For v1 (small rule base, few campaigns), this may feel over-engineered. The counter-argument: the overhead is O(number of stages), not O(number of rules) — with 4-5 pipeline states, the cost is trivial. And under-engineering the integrity mechanism is precisely how the online lineage ended up with 1,692 lines of accumulated contamination.

**Proposed amendment**: Accept mechanism as designed. Scope v1 to discovery pipeline transitions only (4-5 states). Specification work remaining: enumerate states, valid transitions, error handling for invalid transition attempts, and hash computation scope (which artifacts' hashes are included in each transition signature).

### Classification: Thiếu sót

The mechanism is described at a high level but not fully specified. Remaining specification work is expected — this is a design brief, not a finished spec. The mechanism itself is not contested.

---

### Facet F: Filesystem Enforcement — ACCEPT (defense-in-depth)

chmod 444 after verdict as supplementary guardrail (`findings-under-review.md:69`: "defense-in-depth, không phải primary enforcement").

**Key argument**: Correctly positioned as defense-in-depth. The primary enforcement is typed schema + state machine; filesystem permissions are a second barrier for scenarios where code bugs bypass the primary enforcement. This layered approach follows standard security practice (defense-in-depth principle).

Cross-topic interface with Topic 009 (F-11 session immutability) is clear per `README.md` tensions table: Topic 009 owns immutability mechanism (chmod for session artifacts); Topic 002 owns firewall mechanism (typed schema + state machine for meta-knowledge content). Different artifacts, different purposes, no enforcement overlap.

**Proposed amendment**: Accept as designed. No changes needed. This facet is non-controversial and likely near-convergence.

### Classification: Thiếu sót (minor — specification of WHICH artifacts get chmod and WHEN is pending)

---

## Summary

### Accepted (near-convergence candidates)
- **Facet B**: MK-07 permanent resolution — GAP/AMBIGUITY distinction is sound; `STRUCTURAL_PRIOR` retires `UNMAPPED`
- **Facet E**: State machine — accept mechanism, scope v1 to pipeline states
- **Facet F**: Filesystem — accept as defense-in-depth, no controversy

### Challenged (need debate)
- **Facet A**: 5th category (`STRUCTURAL_PRIOR`) — strongest proposed change. Reviewer should challenge: classification test sharpness, dumping-ground risk, whether Path 2 (redefine existing categories) or Path 3 (permanent `UNMAPPED`) is superior
- **Facet C**: `STOP_DISCIPLINE` preservation — conceptual distinction (meta-level vs object-level) vs enforcement-action equivalence. Is a concept-only distinction enough to justify a separate category?
- **Facet D**: `PROVENANCE_AUDIT_SERIALIZATION` deferral — timing question. Is v1 the right time to split, or should we wait for empirical signals?

---

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 004 | MK-07 | F-06 category gap: ~10 Tier 2 structural priors with no category home. MK-07 interim rule revised (GAP ≠ AMBIGUITY). Proposed fix: `STRUCTURAL_PRIOR` category | within this topic |
| 004 | MK-14 | Boundary contract: 002 owns content gate, 004 owns lifecycle gate. Adding `STRUCTURAL_PRIOR` is content vocabulary, not lifecycle state — no boundary crossed | 004 closed; no conflict |
| 009 | F-11 | chmod (002) vs session immutability (009): different artifacts, different purposes. No enforcement overlap | 009 owns immutability; 002 owns firewall |
| 016 | C-12 | Bounded recalibration prima facie incompatible with current firewall categories. `STRUCTURAL_PRIOR` may help: recalibrated priors = mixed content with provenance | 016 owns decision |
| 017 | ESP-02 | Reconstruction-risk gate extends firewall to phenotype layer. `STRUCTURAL_PRIOR` provides category home for phenotype-derived structural priors | 002 owns gap fix; 017 defines phenotype contracts |

---

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-D-04 | Contamination firewall — machine-enforced | Thiếu sót | Open | — | — |

### Facet tracking (internal to X38-D-04)

| Facet | Subject | Author position | Phân loại | Trạng thái |
|---|---|---|---|---|
| A | Category gap for Tier 2 priors | ACCEPT + add `STRUCTURAL_PRIOR` | Thiếu sót | Open |
| B | MK-07 interim rule → permanent fix | ACCEPT amended + permanent via `STRUCTURAL_PRIOR` | Thiếu sót | Open |
| C | `STOP_DISCIPLINE` thinness | REJECT consolidation (keep separate) | Judgment call | Open |
| D | `PROVENANCE_AUDIT_SERIALIZATION` overloading | DEFER split to v2+ | Judgment call | Open |
| E | State machine enforcement | ACCEPT as designed, scope to v1 pipeline | Thiếu sót | Open |
| F | Filesystem enforcement (defense-in-depth) | ACCEPT as designed | Thiếu sót | Open |
