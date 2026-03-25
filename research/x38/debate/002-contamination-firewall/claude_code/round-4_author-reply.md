# Round 4 — Author Reply: Contamination Firewall
**Topic**: 002 — Contamination Firewall
**Author**: claude_code
**Date**: 2026-03-25
**Responds to**: `codex/round-3_reviewer-reply.md`
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
- `debate/002-contamination-firewall/claude_code/round-3_author-reply.md`
- `debate/002-contamination-firewall/codex/round-3_reviewer-reply.md`
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

Codex's Round 3 confirms two §7(c) closures (5th enum rejected, Facet F converged) and narrows the remaining dispute to a single structural question: whether MK-04's provenance test alone suffices to operationalize the design brief's catch-all ban, or whether Topic 002 must specify an additional effect-based criterion. This round concedes on Facet E and proposes convergence, then resolves Facet A as Judgment call contingent on that convergence.

## §7(c) Acknowledgments

**5th mutually exclusive enum**: Codex confirmed §7(c) (`round-3_reviewer-reply.md:42-44`). Sub-point is Converged (rejected). No further action.

**Facet F — Filesystem enforcement**: Codex confirmed §7(c) (`round-3_reviewer-reply.md:48-50`). Facet F is Converged. No further action.

---

## Part A — Steel-Man Attempts

### Facet E: Admissibility Boundary

**Steel-man for my Round 3 position** (MK-04 is sufficient as permanent admissibility criterion for the catch-all boundary):

The ternary framework (MK-02/MK-05) proved binary framing non-viable and created Tier 2 for the middle ground. MK-04's derivation test classifies rules into three outcomes: "Fully YES" (Tier 1), "Partially" (Tier 2), "Fully NO" (blocked). For "Partially" results, `derivation_test.json` already requires explicit `empirical_residue` and `admissibility_rationale` fields (`final-resolution.md:332-338`). The mandatory prose justification forces the reviewer to explain why the data-derived portion does not constitute an answer prior. The artifact structure demands the relevant judgment, and the catch-all boundary is therefore already operationalized per-rule through MK-04 without an additional Topic 002-specific test.

**Why the steel-man does not hold**:

1. **Provenance ≠ effect** (`round-3_reviewer-reply.md:69`). MK-04 measures what portion of a rule is data-derived (PROVENANCE). The design brief's catch-all ban (line 49) measures whether the rule tilts family/architecture/calibration-mode choice (EFFECT). These are correlated but distinct predicates. A rule can satisfy MK-04's "Partially" outcome and simultaneously steer the search space. T2-2 proves this concretely: "microstructure excluded from mainline swing horizon" is partially derivable (noise degradation is axiomatic), but the empirical residue IS a scope exclusion that narrows the architecture/search branch (`input_f06_category_coverage.md:102`; `design_brief.md:49`). MK-04 correctly classifies T2-2 as Tier 2; it does not answer whether T2-2's empirical residue constitutes family/architecture/calibration-mode tilt per the catch-all ban.

2. **No coverage mandate exists for the tilt predicate** (`final-resolution.md:204,332-338`). Topic 004 froze `admissibility_rationale` and mandated "prose justification for data-derived portions." This addresses what IS data-derived, not whether the data-derived portion steers the search space. An implementer can write a valid `admissibility_rationale` that fully explains the data derivation without ever addressing tilt. The gap is not in the artifact structure but in the evaluation specification.

3. **A-2 proves the distinction is operational, not theoretical** (`round-3_reviewer-reply.md:70`; `input_f06_category_coverage.md:105-106`). "14 quarterly folds" has a clean axiomatic component (quarterly folding = common statistical practice) and a BTC-specific component ("14" = ~3.5 years × quarterly). MK-04 correctly identifies partial derivability. But the number "14" hard-codes a dataset-specific calibration default — precisely the kind of calibration-mode tilt the design brief's ban (line 49) and meta-updater section (lines 84-89) target. MK-04's provenance analysis does not distinguish "axiomatic principle + dataset-specific calibration number" from "axiomatic principle + benign empirical observation."

**Conclusion**: I was wrong to claim MK-04 alone constitutes a sufficient permanent admissibility criterion. The evidence proves that provenance mixedness (MK-04's output) and search-space tilt (the design brief's catch-all target) are related but non-identical predicates, and MK-04 addresses only the former.

**Proposed resolution**: Topic 002 specifies a **tilt-assessment coverage mandate** for the `admissibility_rationale` field in `derivation_test.json`. For any rule with MK-04 result "Partially," the `admissibility_rationale` MUST explicitly evaluate:

(a) Whether the empirical residue narrows the set of admissible families, architectures, or calibration modes
(b) If (a) = yes, whether the narrowing selects toward a specific answer (→ blocked per design brief line 49) or constrains the search space without selecting within it (→ bounded per design brief lines 53-54, admitted as Tier 2)

This does not duplicate MK-04 — it operates on MK-04's output. MK-04 determines provenance; the tilt mandate determines effect. Both evaluations are recorded in the same `derivation_test.json` artifact, within the existing `admissibility_rationale` field. No new artifact, no new field, no amendment to Topic 004's frozen spec. The mandate is a content-gate specification (Topic 002 territory per MK-14, `final-resolution.md:190`), not a governance-gate change.

Concrete application to the disputed examples:

- **V5-3** "slower context + faster persistence complement": MK-04 = Partially. Tilt: observes complementarity pattern, does not exclude any family/architecture from the search space. → Admissible.
- **T2-2** "microstructure excluded from swing horizon": MK-04 = Partially. Tilt: excludes a TF regime. But the narrowing constrains without selecting — it removes noise-dominated frequencies without implying which strategy, family, or winner within the remaining space is correct. → Admissible with documented justification that the exclusion is scope-limiting, not answer-selecting.
- **A-2** "14 quarterly folds": MK-04 = Partially. Tilt: "quarterly" = clean principle. "14" = dataset-specific numeric calibration default. → Principle admissible; numeric component must be generalized (e.g., "quarterly folding scaled to dataset length") to avoid calibration-mode tilt. The specific number is stripped or parametrized as a protocol-engine default, not frozen as a structural prior.

**Proposed status**: Converged — waiting for Codex to confirm §7(c).

---

## Part B — Continued Debate

### Facet A: Pure-Gap Rules

Codex correctly identifies that the pure-gap set is contingent on the admissibility boundary (`round-3_reviewer-reply.md:62`): until the boundary is fixed, the size and composition of the permanent gap remain unstable. If Facet E converges on the tilt-assessment mandate, the set stabilizes: rules that pass both MK-04 and the tilt assessment are admissible UNMAPPED rules; rules whose empirical residue constitutes search-space tilt are blocked or require component generalization (like A-2's numeric stripping).

Codex's three objections to my Round 3 options all hold on the evidence:

1. **Option 3** (`structural_prior: boolean`) does not provide content-type discrimination — it re-labels the cross-cutting property already in `empirical_residue` without distinguishing scope exclusion from price-structure observation from empirical summary (`round-3_reviewer-reply.md:58`). The claimed defect ("F-06 no longer says WHAT the rule is") is not repaired by a single boolean.

2. **Option 2** (minimal absorption) documents that the whitelist doesn't cover these rules — a problem statement, not a proportionate fix (`round-3_reviewer-reply.md:59`).

3. **Option 1** (UNMAPPED permanent) has a safe provisional route via Topic 004's amended MK-07 (`final-resolution.md:373-392`), and no concrete operational failure from that route has been demonstrated at v1 scale (`round-3_reviewer-reply.md:60`).

With Facet E settled, the admissible pure-gap set likely comprises ~3-4 rules (V5-3, V5-4, CS-6 clearly admissible; T2-2 admissible with justification; A-2 admissible after numeric generalization). At this scale, UNMAPPED + governance routing (Tier 2 + SHADOW per MK-17) is proportionate for v1. The structural concern about F-06 coverage is real — UNMAPPED is definitionally a failure of the content-classification layer — but the harm at ~3-4 rules is bounded, governance routing is safe, and none of the proposed vocabulary fixes satisfy the requirements without introducing their own problems.

**Proposed disposition**: Judgment call. The remaining tradeoff is genuine:

- **For fixing at v1**: F-06's stated purpose is content classification; UNMAPPED = permanent coverage gap on the rules MK-02 identifies as highest-risk (information laundering, `input_f06_category_coverage.md:109-117`). Documented limitation risks normalization.
- **For UNMAPPED at v1**: ~3-4 rules, safe governance routing, no concrete failure, vocabulary expansion should be evidence-driven (wait for more rules to determine the right category boundaries rather than speculating on a taxonomy for 3-4 rules).

Decision owner: human researcher (§15). The mechanism is settled (UNMAPPED + governance = fallback; vocabulary expansion = fix path); the timing/proportionality tradeoff is not resolvable by evidence alone.

### Facet B (author): MK-07 Interim → Permanent

Contingent on Facets A + E, as previously stated. If Facet E converges (tilt-assessment mandate) and Facet A resolves as Judgment call:

- **If human researcher chooses "UNMAPPED at v1"**: MK-07's amended GAP path (`final-resolution.md:373-392`) becomes the permanent v1 handling. `UNMAPPED` tag persists, Tier 2 + SHADOW governance applies, review obligation when rule base grows.
- **If human researcher chooses "fix at v1"**: Topic 002 specifies a new F-06 category for admissible pure-gap rules. `UNMAPPED` tag retires for rules that gain a category home.

In both cases, the GAP/AMBIGUITY distinction from the amended MK-07 is preserved: AMBIGUITY (multiple categories fit) remains fail-closed; GAP (no category fits) remains admitted via UNMAPPED. The only open question is whether UNMAPPED is permanent at v1 or replaced by vocabulary expansion — the same Judgment call as Facet A.

**Proposed status**: Judgment call (follows from Facet A disposition). Same decision owner, same tradeoff.

---

## Cross-topic tensions (updated)

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 004 | MK-07 | F-06 category gap: ~3-4 admissible pure-gap rules at v1 (contingent on Facet E tilt assessment). UNMAPPED permanent vs vocabulary expansion = Judgment call | within this topic |
| 004 | MK-14 | Boundary preserved: tilt-assessment mandate operates within existing `derivation_test.json` artifact's `admissibility_rationale` field, maintaining single-ownership per MK-14 | 004 closed; no conflict |
| 009 | F-11 | chmod (002) vs session immutability (009): different artifacts, different purposes. Converged (Facet F) | 009 owns immutability; 002 owns firewall |
| 016 | C-12 | Bounded recalibration: admissibility boundary now has explicit tilt-assessment criterion. Recalibrated priors that pass both MK-04 and tilt assessment = Tier 2, admitted with governance | 016 owns decision |
| 017 | ESP-02 | Reconstruction-risk gate: phenotype-derived structural priors handled by derivation_test metadata + tilt-assessment mandate. Pure-gap phenotype priors → UNMAPPED or vocabulary expansion (Judgment call) | 002 owns gap fix; 017 defines phenotype contracts |

---

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-D-04 | Contamination firewall — admissibility boundary proposed converged (tilt-assessment mandate); pure-gap handling + MK-07 permanent = Judgment call | Thiếu sót | Open (pending Facet E §7(c)) | — | — |

### Facet tracking (internal to X38-D-04)

| Facet | Subject | Round 4 position | Phân loại | Trạng thái |
|---|---|---|---|---|
| A | Category gap — mechanism | 5th enum Converged (rejected). Straddling rules resolved. Pure-gap rules (~3-4 after tilt assessment): UNMAPPED at v1 vs vocabulary expansion = genuine proportionality tradeoff. No concrete v1 failure from UNMAPPED; F-06 coverage concern real but bounded at ~3-4 rules | Thiếu sót | **Judgment call** (proposed) |
| B (author) | MK-07 interim → permanent | Contingent on A + E. GAP/AMBIGUITY distinction preserved. UNMAPPED permanent or vocabulary expansion = same Judgment call as Facet A | Thiếu sót | **Judgment call** (proposed) |
| B (Codex) | `PROVENANCE_AUDIT_SERIALIZATION` overload | Both sides agree: overload real, split-now not proved. Timing tradeoff | Judgment call | **Judgment call** |
| C | `STOP_DISCIPLINE` thinness | Converged (Round 2) | Judgment call | **Converged** |
| D (Codex) | State machine complexity | Converged (Round 2) | Thiếu sót | **Converged** |
| E (Codex) | Admissibility boundary | Concession: MK-04 alone insufficient (provenance ≠ effect). Proposed: tilt-assessment coverage mandate on `admissibility_rationale` — must evaluate whether empirical residue steers family/architecture/calibration-mode. Operates within existing artifact, no Topic 004 amendment needed | Thiếu sót | **Converged** (proposed, waiting §7(c)) |
| F (author) | Filesystem enforcement | Converged (Round 3, §7(c) confirmed by Codex Round 3) | Thiếu sót | **Converged** |
