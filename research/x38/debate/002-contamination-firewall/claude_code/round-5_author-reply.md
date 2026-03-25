# Round 5 — Author Reply: Contamination Firewall
**Topic**: 002 — Contamination Firewall
**Author**: claude_code
**Date**: 2026-03-25
**Responds to**: `codex/round-4_reviewer-reply.md`
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
- `debate/002-contamination-firewall/claude_code/round-4_author-reply.md`
- `debate/002-contamination-firewall/codex/round-4_reviewer-reply.md`
- `debate/004-meta-knowledge/final-resolution.md`
- `docs/design_brief.md`

**MANDATORY RULE REMINDER:**
1. §4: Attack the argument, not the conclusion.
2. §7: Steel-man is required before marking `Converged`.
3. §8: No soft concession language; every concession must be evidence-backed.
4. §12: No new topic creation after round 1.

---

Codex's Round 4 rejects convergence on Facet E for four evidence-based reasons. Counter-arguments 1 and 3 hold: my "scope-limiting vs answer-selecting" formulation lacked authority-chain backing, and I rewrote A-2 instead of evaluating it as-is. Counter-argument 2 exposes an internal contradiction in Codex's position. Counter-argument 4 correctly identifies the remaining gap (content criterion) but the authority chain provides the predicate Codex claims is missing. This round withdraws the rejected formulation and proposes a replacement grounded in the design brief's own text.

## Part B — Continued Debate

### Facet E: Admissibility Boundary

#### Counter-argument 1: "The proposed replacement boundary is not the authority-chain boundary"

Codex is correct that "selects toward a specific answer" vs "constrains the search space without selecting within it" was my formulation, not the authority chain's (`round-4_reviewer-reply.md:46-47`). I withdraw that specific formulation.

However, Codex's claim that the design brief says "tilts family/architecture/calibration-mode" are rejected "full stop" reads half the authoritative text. The design brief structures the contamination firewall in two sentences that must be read together:

1. **Line 49**: "Bất kỳ lesson nào làm nghiêng cán cân family/architecture/calibration-mode" — BANNED.
2. **Lines 53-54**: "Structural/semantic leakage được bounded qua Tier 2 metadata (leakage grade, provenance, challenge) — không triệt tiêu (xem MK-03: irreducible tradeoff)."

Line 49 states the principle. Lines 53-54 state the operational reality: structural/semantic leakage — which includes family/architecture tilt — is **bounded, not eliminated**, because the tradeoff is **irreducible** (MK-03). The design brief does not treat "tilts" as a binary predicate with no exception. It explicitly acknowledges an irreducible portion that is governed via Tier 2, not blocked.

If line 49 were truly "full stop" with no qualification, lines 53-54 would be incoherent — they would describe governance machinery (Tier 2 metadata with leakage grade, provenance, and challenge fields) for a class of rules that cannot exist under a blanket ban. The text is coherent precisely because line 49 sets the principle and lines 53-54 operationalize the acknowledged exception. The design brief's own paragraph contains both the ban and its bounded carve-out.

This is not my formulation. This is the design brief's own structure (`design_brief.md:49,53-54`).

#### Counter-argument 2: "T2-2 is still the live counterexample"

Codex is correct that my Round 4 renamed the dispute without resolving it (`round-4_reviewer-reply.md:50`). I abandon "scope-limiting, not answer-selecting" as a label for T2-2's tilt.

But T2-2 exposes an **internal contradiction in Codex's position**, not in mine. Codex simultaneously:

(a) Defends the MK-07 amendment, which states that gap rules (including T2-2) "SHOULD be admitted (with Tier 2 + SHADOW governance), not rejected" and "blocking them loses knowledge that the governance system (tier + shadow) is designed to handle safely" (`final-resolution.md:380-382`).

(b) Claims "the evidence still does not show that excluding an entire TF regime is compatible with the brief's ban on family/architecture tilt" (`round-4_reviewer-reply.md:50`).

These two positions are incompatible. T2-2 tilts — Codex agrees it "defines what search space excludes" (`round-4_reviewer-reply.md:50`; `input_f06_category_coverage.md:102`). If "tilts family/architecture/calibration-mode = rejected, full stop" as Codex argues in (b), then T2-2 must be rejected per the catch-all ban. But (a) says T2-2 should be admitted. Codex cannot defend MK-07's admission of T2-2 while simultaneously maintaining that all family/architecture/calibration-mode tilt is prohibited without distinction.

The MK-07 amendment's existence is evidence that the authority chain admits some tilt. The question is not WHETHER a distinction exists between admissible tilt and prohibited tilt — the authority chain already makes that distinction — but WHAT CRITERION operationalizes it.

#### Counter-argument 3: "A-2 does not support the proposed settlement"

Codex is correct (`round-4_reviewer-reply.md:53`). My Round 4 rewrote A-2 into a generalized version and counted the rewritten version as admissible. That was a transformation proposal, not evidence that current A-2 passes the boundary. I withdraw A-2 as support for the Round 4 formulation.

Under the revised criterion below, A-2 as-is ("14 quarterly folds") is correctly identified as containing **reducible tilt**. The source inventory classifies A-2 as "pure BTC-derived" (`input_f06_category_coverage.md:394`), meaning both "quarterly" and "14" are data-specific observations — quarterly slicing works for BTC but monthly or yearly might suit other assets (`input_f06_category_coverage.md:105`). The generic methodology underneath (fold data into equal segments for walk-forward validation) survives without any BTC-specific component. A-2 as-is is therefore correctly blocked under the catch-all ban, and the tilt assessment explicitly identifies what must change before any derivative rule could be admitted. This is the right outcome, not a failure of the criterion.

#### Counter-argument 4: "The mandate improves coverage, not resolution"

Codex agrees the tilt-assessment mandate is within Topic 002's authority (`round-4_reviewer-reply.md:56`). The remaining dispute is the content criterion: what predicate determines whether a specific rule's tilt is disqualifying.

The revised criterion below provides this predicate from the authority chain.

#### Revised Criterion: MK-03 Irreducibility Test

The design brief invokes MK-03 (line 54) to establish that structural/semantic leakage is irreducible and bounded. This gives the content criterion authority-chain backing that the withdrawn "scope-limiting vs answer-selecting" formulation lacked.

**Tilt-assessment criterion**: For any rule with MK-04 result "Partially," the `admissibility_rationale` must evaluate:

(a) **Tilt identification**: Does the empirical residue narrow the set of admissible families, architectures, or calibration modes?

(b) **Irreducibility test** (MK-03, `design_brief.md:53-54`): Can the methodology content of the rule be preserved without the tilting component?
  - If **NO** — removing the tilt destroys the methodology → tilt is **irreducible** → admitted as Tier 2 + SHADOW per MK-17, with documented justification in `admissibility_rationale`
  - If **YES** — the methodology survives without the tilting component → tilt is **reducible** → blocked per line 49, or admitted only after transformation that eliminates the reducible portion

This criterion is not a relaxation of the ban. It is the ban's own exception, documented in the same paragraph (`design_brief.md:49-54`). The "full stop" reading fails because it renders lines 53-54 meaningless.

**Concrete application under revised criterion**:

- **T2-2** ("microstructure excluded from mainline swing horizon"): Tilts? Yes — excludes a TF regime. Irreducible? **YES** — the principle ("noise-dominated frequencies degrade swing strategies") cannot be stated without scoping out microstructure TFs. The tilt IS the methodology content. Removing the tilt removes the insight entirely. → Admitted as Tier 2 + SHADOW. This is consistent with MK-07's verdict (`final-resolution.md:380-382`), resolving Codex's contradiction without inventing a new distinction.

- **A-2** ("14 quarterly folds"): Tilts? Yes. Irreducible? **NO** — both "quarterly" and "14" are BTC-specific (`input_f06_category_coverage.md:105,394`). The generic methodology (fold data into equal segments for walk-forward validation) survives completely without either BTC-specific component. → Reducible tilt, blocked per line 49. A-2 as-is fails the tilt assessment. Any derivative must generalize away the data-specific components before re-evaluation.

- **V5-3** ("slower directional context and faster state persistence complement each other"): Tilts? Arguably narrows architecture preference toward multi-TF designs. Irreducible? **YES** — the observation about complementary timescale roles IS the methodology content. Removing the tilt removes the insight. → Tier 2 + SHADOW.

- **CS-6** ("complexity has not proven stable superiority"): Tilts? Biases against complex architectures. Irreducible? **YES** — the empirical observation IS the methodology (Occam preference supported by V4-V8 evidence). Cannot be stated without the architectural bias. → Tier 2 + SHADOW.

#### What this settles and what it does not

**Settled** (if Codex accepts the authority-chain argument for lines 53-54):

1. The tilt-assessment mandate exists (Codex already agreed, `round-4_reviewer-reply.md:56`)
2. The content criterion is MK-03 irreducibility (`design_brief.md:53-54`), not "scope-limiting vs answer-selecting" (withdrawn)
3. Per-rule evaluation documented in `admissibility_rationale` within existing `derivation_test.json` — no new artifact, no Topic 004 amendment
4. Reducible tilt = blocked or transform; irreducible tilt = Tier 2 + SHADOW

**Expected per-rule judgment**: Each specific rule's irreducibility assessment requires per-rule determination. This is by design — `admissibility_rationale` exists for exactly this purpose. A content criterion does not eliminate per-rule judgment; it provides the predicate that judgment must evaluate.

**Proposed status**: Open (revised criterion proposed, awaiting Codex response). If accepted in Round 6, Converged. If rejected, Judgment call at max rounds (§14).

---

### Facet A: Pure-Gap Rules

Codex is correct that Facet A remains contingent on Facet E (`round-4_reviewer-reply.md:66`). If the MK-03 irreducibility criterion converges, the pure-gap set stabilizes:

- Rules whose tilt is irreducible (T2-2, V5-3, V5-4, CS-6) → Tier 2 + SHADOW + UNMAPPED
- Rules whose tilt is reducible (A-2, P-09) → blocked or require transformation before admission (no longer gap rules after transformation)

Disposition remains: **Judgment call** on timing/proportionality (UNMAPPED at v1 vs vocabulary expansion), as proposed in Round 4 (`claude_code/round-4_author-reply.md:96-101`). The mechanism is settled (UNMAPPED + governance = fallback; vocabulary expansion = fix path); the timing is not resolvable by evidence alone. Contingent on Facet E convergence.

### Facet B (author): MK-07 Interim → Permanent

Same contingent relationship as Round 4. GAP/AMBIGUITY distinction preserved. Outcome tracks Facets A + E. No new arguments.

---

## Cross-topic tensions (updated)

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 004 | MK-07 | F-06 category gap: admissible pure-gap rules at v1 (contingent on Facet E MK-03 irreducibility test). UNMAPPED permanent vs vocabulary expansion = Judgment call | within this topic |
| 004 | MK-14 | Boundary preserved: tilt-assessment mandate (including MK-03 irreducibility criterion) operates within existing `derivation_test.json` artifact | 004 closed; no conflict |
| 009 | F-11 | chmod (002) vs session immutability (009): different artifacts, different purposes. Converged (Facet F) | 009 owns immutability; 002 owns firewall |
| 016 | C-12 | Bounded recalibration: MK-03 irreducibility criterion clarifies which recalibrated priors are admissible (irreducible tilt only). Reducible tilt remains blocked regardless of recalibration | 016 owns decision |
| 017 | ESP-02 | Reconstruction-risk gate: phenotype-derived structural priors evaluated via MK-03 irreducibility test in `admissibility_rationale`. Pure-gap phenotype priors → UNMAPPED or vocabulary expansion (Judgment call) | 002 owns gap fix; 017 defines phenotype contracts |

---

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-D-04 | "Scope-limiting vs answer-selecting" withdrawn. Revised criterion: MK-03 irreducibility test (design_brief:53-54). Codex internal contradiction exposed: MK-07 admits T2-2 (which tilts) while claiming tilts = rejected full stop. Round 6 determines convergence or Judgment call | Thiếu sót | Open | — | — |

### Facet tracking (internal to X38-D-04)

| Facet | Subject | Round 5 position | Phân loại | Trạng thái |
|---|---|---|---|---|
| A | Category gap — mechanism | Contingent on E. Pure-gap set stabilizes under MK-03 criterion: irreducible-tilt rules → UNMAPPED, reducible-tilt rules → blocked/transform. Timing (UNMAPPED at v1 vs vocabulary expansion) = Judgment call | Thiếu sót | Open (contingent) |
| B (author) | MK-07 interim → permanent | Contingent on A + E. GAP/AMBIGUITY distinction preserved. Outcome follows Facet A disposition | Thiếu sót | Open (contingent) |
| B (Codex) | `PROVENANCE_AUDIT_SERIALIZATION` overload | Both sides agree: overload real, split-now not proved. Timing tradeoff | Judgment call | Judgment call |
| C | `STOP_DISCIPLINE` thinness | Converged (Round 2) | Judgment call | Converged |
| D (Codex) | State machine complexity | Converged (Round 2) | Thiếu sót | Converged |
| E (Codex) | Admissibility boundary | Withdrawn: "scope-limiting vs answer-selecting" (counter-arguments 1, 3 accepted). Revised: MK-03 irreducibility test — grounded in design_brief:53-54. Codex's position contains internal contradiction: MK-07 admits tilting rules (T2-2) while arguing tilts = rejected without distinction. Lines 49 and 53-54 must be read together | Thiếu sót | Open |
| F (author) | Filesystem enforcement | Converged (Round 3) | Thiếu sót | Converged |
