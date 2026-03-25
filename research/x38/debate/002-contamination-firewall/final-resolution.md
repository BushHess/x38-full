# Final Resolution — Contamination Firewall

**Topic ID**: X38-T-02
**Closed**: 2026-03-25
**Rounds**: 6 / 6 (max_rounds_per_topic per §13)
**Participants**: claude_code (author), codex (reviewer)

## Round Symmetry

Both agents submitted 6 round artifacts (R1–R6). No §14b asymmetry.

## Summary

Topic 002 debated 1 finding (X38-D-04) across 7 internal facets through 6 rounds.
Debate narrowed progressively: facets C, D, and F converged in rounds 2–3. The
remaining dispute centered on Facet E (admissibility boundary for structural priors)
and its contingent facets A and B-author. By round 6, both sides agreed that the
authority chain does not source a concrete per-rule admissibility criterion for
structural priors (`claude_code/round-6_author-reply.md:62-67`;
`codex/round-6_reviewer-reply.md:41`). The remaining choice converted to Judgment
call per §14.

**Final tally**: 3 Converged, 4 Judgment call (decided by human researcher). All
7 facets resolved. No open items.

---

## Decisions

| Facet | Subject | Resolution | Type | Round closed |
|-------|---------|------------|------|-------------|
| C | STOP_DISCIPLINE thinness | Keep as separate category — 3 rules justify dedicated bucket | Converged | 2 |
| D (Codex) | State machine complexity | Acceptable for v1 — hash-signing transitions is core enforcement, not optional complexity | Converged | 2 |
| F (author) | Filesystem enforcement | chmod 444 is defense-in-depth guardrail, not primary enforcement. Primary = typed schema + state machine | Converged | 3 |
| E | Admissibility boundary | No new positive admissibility criterion frozen by Topic 002. Permanent `UNMAPPED + Tier 2 + SHADOW` governance path for pure-gap structural priors. 4 named F-06 categories and `design_brief.md:49` ban unchanged | Judgment call (§14) → human decision | 6 |
| A | Category gap — mechanism | No v1 vocabulary expansion. Keep 4 named F-06 categories. No `STRUCTURAL_PRIOR`, no content-annotation addition, no force-fit | Judgment call (§14) → human decision | 6 |
| B (author) | MK-07 interim → permanent | MK-07 amended handling (GAP/AMBIGUITY distinction) adopted as permanent law for Topic 002. `UNMAPPED` is governance tag, not 5th content category. Tag does not retire in v1 | Judgment call (§14) → human decision | 6 |
| B (Codex) | PROVENANCE_AUDIT_SERIALIZATION overload | Defer split. Keep single bucket for v1 | Judgment call (§14) → human decision | 6 |

---

## §14 Judgment-Call Decisions (2026-03-25)

**Decision owner**: Human researcher (per §15).
**Decision criteria**: authority chain faithfulness (burden of proof on change
proposer per `debate/rules.md:21-22`), v1 simplicity, permanent closure (no
"interim until bootstrap" deferrals).

### Facet E — No New Positive Admissibility Criterion

**Direction**: Topic 002 does not freeze a new positive admissibility criterion for
structural-prior gap rules. The permanent governance path is `UNMAPPED + Tier 2 +
SHADOW`, as already opened by Topic 004
(`debate/004-meta-knowledge/final-resolution.md:389-392`).

**Reasoning**:

1. `docs/design_brief.md:46-49` and `findings-under-review.md:59-61` maintain the
   firewall on 4 whitelist buckets and ban lessons that tilt
   family/architecture/calibration-mode.
2. By round 6, both agents agreed that the authority chain does not source a concrete
   per-rule criterion. MK-03 irreducibility was a proposal, not existing law
   (`claude_code/round-6_author-reply.md:62-67`;
   `codex/round-6_reviewer-reply.md:41`).
3. Per `debate/rules.md:21-22` (§5), burden of proof belongs to the side proposing
   change. The proposed criterion was not proven.
4. MK-15 (bootstrap, `004-meta-knowledge/final-resolution.md:191`) specifies
   "classify via derivation test, tag provenance, all Tier 2 = SHADOW." It does
   not create a step for inventing a new admissibility criterion.
5. This does not deny that some `Partially` rules survive. MK-04's
   `admissibility_rationale` (`004-meta-knowledge/final-resolution.md:332-340`)
   continues to serve rules whose data residue does NOT tilt
   family/architecture/calibration-mode. The decision only refuses to create a
   special positive rule for pure-gap structural priors whose primary content tilts.

**This is a permanent v1 choice**, not an interim pending bootstrap or future
criterion development.

### Facet A — No V1 Vocabulary Expansion

**Direction**: Keep 4 named F-06 categories: `PROVENANCE_AUDIT_SERIALIZATION`,
`SPLIT_HYGIENE`, `STOP_DISCIPLINE`, `ANTI_PATTERN`. No 5th category, no
`STRUCTURAL_PRIOR`, no content-annotation additions, no force-fitting.

**Handling by rule class**:
- Rules with a primary existing home → keep primary category + `derivation_test`
  metadata
- Genuine pure-gap rules (~10 Tier 2 structural priors) → permanent `UNMAPPED`
  (governance tag, not content category)
- Genuine ambiguity (rule plausibly maps to multiple categories; in current
  inventory, only V8-3) → non-admissible pending human review (fail-closed)

**Rejected alternatives**:
- 5th mutually exclusive enum `STRUCTURAL_PRIOR` — not added
- `structural_prior: boolean` cross-cutting annotation — relabels the same property
  without providing content-type signal (`codex/round-3_reviewer-reply.md`)

### Facet B (author) — MK-07 Amended Handling Becomes Permanent Law

**Direction**: The GAP/AMBIGUITY distinction from Topic 004's MK-07 amendment
(`debate/004-meta-knowledge/final-resolution.md:373-392`) is adopted as permanent
law for Topic 002:

- **GAP** (rule fits no category without stretching): permanent `UNMAPPED` + Tier 2
  + SHADOW. `UNMAPPED` is a governance tag (Topic 004 territory), not a 5th F-06
  content category (Topic 002 territory). Tag does NOT retire in v1.
- **AMBIGUITY** (rule plausibly maps to multiple categories): non-admissible pending
  human review. Fail-closed is correct because the rule IS within F-06's scope — the
  question is which category, not whether to admit.

**Fork chosen**: Topic 004 documented two paths
(`final-resolution.md:389-392`): "if Topic 002 adds a category → retire UNMAPPED;
if not → UNMAPPED + Tier 2 + SHADOW becomes permanent path." **Topic 002 chooses
the second fork.** This is a permanent closure choice.

### Facet B (Codex) — Defer PROVENANCE_AUDIT_SERIALIZATION Split

**Direction**: Keep `PROVENANCE_AUDIT_SERIALIZATION` as a single bucket for v1.

**Reasoning**:
1. `docs/design_brief.md:40-41` already groups provenance/audit/serialization as
   one allowed-transfer class.
2. `input_f06_category_coverage.md §4` describes the distribution as "unbalanced
   but functional."
3. In the current inventory, only V8-3 is genuinely ambiguous between two existing
   buckets (`input_f06_category_coverage.md:137`).
4. Both sides in rounds 2, 3, and 6 agreed: overload is real, split-now not proven,
   remainder is timing/granularity tradeoff.

**Reopen trigger**: actual implementation confusion or workflow/validation paths that
genuinely diverge within the bucket. No frozen numeric threshold (e.g., ">40 rules")
in spec.

---

## Key Design Decisions (for drafts/)

### Decision 1: Typed Schema with 4 Whitelist Categories (Permanent)

**Accepted position**: `MetaLesson` typed schema with 4 F-06 categories
(`PROVENANCE_AUDIT_SERIALIZATION`, `SPLIT_HYGIENE`, `STOP_DISCIPLINE`,
`ANTI_PATTERN`). Category whitelist enforcement: lesson with category outside
whitelist is rejected. Lesson with content in family/architecture/calibration-mode
is rejected for mapped categories and genuine ambiguity; pure-gap structural priors
follow permanent `UNMAPPED + Tier 2 + SHADOW` governance path per Topic 004.

**Rejected alternatives**:
- 5th category `STRUCTURAL_PRIOR` — not added (Facet A)
- `structural_prior: boolean` annotation — rejected as relabeling (Facet A)
- MK-03 irreducibility criterion — not source-backed (Facet E)

**Rationale**: `docs/design_brief.md:40-49` (allowed/banned transfer classes),
`004-meta-knowledge/final-resolution.md:345-347` (F-06 ⊥ tier, vocabulary ownership
= Topic 002), `debate/rules.md:21-22` (burden of proof on change proposer)

### Decision 2: State Machine Hash-Signing for Protocol Transitions

**Accepted position**: Each stage transition signed by hash of existing artifacts.
Contamination log only readable after `frozen_spec.json` hash exists. State machine
prevents rollback (FROZEN → SCANNING is invalid transition).

**Rejected alternative**: State machine too complex for v1 — rejected in round 2
(Facet D convergence). Hash-signing is core enforcement.

**Rationale**: `findings-under-review.md:63-66`, CONTAMINATION_LOG_V4
[extra-archive] (8 rounds of actual contamination proves honor-based isolation
insufficient)

### Decision 3: Filesystem chmod as Defense-in-Depth

**Accepted position**: chmod 444 after verdict is supplemental guardrail, not primary
enforcement. Primary enforcement = typed schema + state machine.

**Rejected alternative**: chmod as primary enforcement — rejected because filesystem
permissions alone cannot catch semantic leakage.

**Rationale**: `docs/design_brief.md:55`, `findings-under-review.md:68-70`.
Converged round 3 (Facet F).

### Decision 4: Permanent UNMAPPED Governance for Gap Rules

**Accepted position**: ~10 Tier 2 structural priors with no F-06 category home
receive permanent `UNMAPPED` (governance tag) + Tier 2 + SHADOW treatment. Tag does
not retire in v1. This is Topic 004's second fork
(`004-meta-knowledge/final-resolution.md:389-392`), chosen by Topic 002.

**Rejected alternative**: New positive admissibility criterion (MK-03 irreducibility
test) to admit gap rules as positive firewall content — not source-backed, and
proposed branch condition admitted specimens the record flags as Harm #3 risk
(`input_f06_category_coverage.md:97,102-103`;
`004-meta-knowledge/findings-under-review.md:114-116`).

**Rationale**: `docs/design_brief.md:49` (catch-all ban),
`004-meta-knowledge/final-resolution.md:378-392` (UNMAPPED + permanent fallback),
`debate/rules.md:21-22` (burden of proof), both-agent round-6 agreement that
authority chain does not contain per-rule criterion

### Decision 5: GAP/AMBIGUITY Distinction as Permanent Law

**Accepted position**: Topic 004 MK-07 amended handling adopted permanently:
- GAP → `UNMAPPED` + Tier 2 + SHADOW (permanent governance)
- AMBIGUITY → non-admissible pending human review (fail-closed)

**Rejected alternative**: Single "ambiguous → non-admissible" rule for both cases —
rejected by Topic 004 MK-07 investigation which showed it blocks rules that should
be admitted (`004-meta-knowledge/final-resolution.md:366-371`).

**Rationale**: `004-meta-knowledge/final-resolution.md:373-392` (amended rule, now
permanent per Topic 002 closure)

---

## Unresolved Tradeoffs (for human review)

None. All 4 Judgment calls decided by human researcher. No open items.

---

## Cross-Topic Impact

| Topic | Finding | Impact of Topic 002 closure | Action needed |
|-------|---------|-------------------------------|---------------|
| 004 | MK-07 | Second fork chosen: `UNMAPPED + Tier 2 + SHADOW` permanent. Topic 002 declined category expansion | Update `004-meta-knowledge/final-resolution.md` MK-07 addendum to reference 002 closure |
| 004 | MK-14 | Boundary contract intact. Topic 002 owns content gate (4 categories + `UNMAPPED` governance). Topic 004 owns lifecycle gate. No conflict | None |
| 009 | F-11 | chmod (002) and session immutability (009) confirmed as different mechanisms for different purposes. Converged in Facet F | None |
| 016 | C-12 | Bounded recalibration constrained: recalibrated priors with family/architecture/calibration-mode tilt still banned for mapped categories. Pure-gap structural priors via `UNMAPPED` governance. 016 designs recalibration within these constraints | 016 owns decision |
| 017 | ESP-02 | Reconstruction-risk gate: phenotype-derived structural priors evaluated within existing F-06 categories + `UNMAPPED`. No new category or criterion from 002. 017 defines phenotype contracts within this boundary | 017 owns phenotype contracts |

---

## Draft Impact

| Draft | Sections affected | Action needed |
|-------|------------------|---------------|
| `architecture_spec.md` | §7 (Contamination Firewall — Enforcement Mechanism) | **Fill stub**: typed schema, state machine hash-signing, chmod defense-in-depth, 4 F-06 categories (permanent), `UNMAPPED` governance path |
| `meta_spec.md` (not yet started) | Content rules section (MK-14 interface) | **When started**: firewall content rules — 4 categories, catch-all ban, `UNMAPPED` governance, GAP/AMBIGUITY permanent distinction |

---

## Residual Notes

- **Contamination Log V3** (1191 lines) was not read during debate. V4 (1692 lines)
  was read structurally (2026-03-19). V4 is the latest and sufficient for
  enforcement design decisions. V3 non-reading is not a gap.
- **Burden-of-proof alignment**: Facet E was resolved by §5 (burden on change
  proposer) applied to the proposed MK-03 irreducibility criterion. The criterion
  was cleaner than round 4's "scope-limiting vs answer-selecting" but still not
  source-backed.
- **Round symmetry**: Both agents at 6/6. Codex's round-6 reply
  (`codex/round-6_reviewer-reply.md`) confirmed author's concessions and narrowed
  the judgment call framing: the conservative branch is not "perpetual limbo" but
  the permanent `UNMAPPED` fallback path already documented by Topic 004.
