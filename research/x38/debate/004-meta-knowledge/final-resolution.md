# Final Resolution — Topic 004: Meta-Knowledge Governance

**Topic ID**: X38-T-04
**Opened**: 2026-03-18
**Closed**: 2026-03-21
**Rounds used**: 6 / 6 (max_rounds_per_topic reached per §13)
**Debaters**: claude_code (author), codex (reviewer)

---

## Summary

Topic 004 debated 17 findings (MK-01→MK-17) and 6 critique items (C1→C6) across
two stages:

- **Stage 1A** (rounds 1–2): MK-01→MK-07 + C1, C2
- **Stage 1B** (rounds 3–6): MK-08→MK-15 + C3→C6
- **Pre-debate**: MK-16 (converged, pre-debate), MK-17 (RESOLVED)

**Final tally**: 16 Converged, 5 Judgment call (§14 → human researcher), 2 pre-debate resolved.
All 23 issues resolved. No open items.

---

## §14 Resolution of Stage 1A Near-Convergence Issues

Five issues reached substantive agreement in round 2 but did not complete the
formal §7(a)(b)(c) protocol before max_rounds was consumed by Stage 1B. Per §14,
these convert to Judgment calls with tradeoff documentation. Per §15,
`decision_owner = human researcher`.

### X38-MK-03 — Fundamental Constraint (Learning vs Independence)

**Substantive agreement** (round 2): Both sides agree: (1) same-dataset boundary
is resolved by MK-17 (shadow-only); (2) operating point must be configurable per
context, not a constant; (3) v2+ calibration requires multi-asset evidence not yet
available.

**§7(a) — Steel-man of author's old position**: Nếu issue chỉ nói "operating point
phải configurable" mà không ràng buộc mức tối thiểu về context declaration, thì v2+
có thể trượt thành khẩu hiệu rỗng và mở cửa cho context-matching tùy tiện
(proposed by codex, `codex/round-2_reviewer-reply.md:94-96`).

**§7(b) — Why it does not stand**: Same-dataset boundary IS concrete (MK-17
resolved). V2+ calibration genuinely requires evidence not yet available — premature
specification would be speculation. The fix is recording a v2+ obligation (minimum
context declaration requirement) in the design brief, not forcing calibration now.
(`claude_code/round-2_author-reply.md:193-209`).

**Remaining tradeoff**: v1 spec says "configurable" without constraining HOW v2+
implements it. Risk: v2+ designers take this as permission to do anything. Mitigation:
record minimum requirement that v2+ context declaration must include dataset identity
and contamination lineage.

**Classification**: Judgment call (§14, near-convergence).
**Decision_owner**: Human researcher.

---

### X38-MK-04 — Derivation Test

**Substantive agreement** (round 2): Both sides agree: (1) derivation test is an
admissibility lens, not force calibration; (2) test is human-performed, not
automatable; (3) "Partially" result requires judgment; (4) force lives in governance
layer (policy object), not in the test itself.

**§7(a) — Steel-man of author's old position**: Finding hiện mô tả derivation test
là "operational, auditable criterion", nhưng nếu không ràng buộc output artifact cho
phần lập luận "Partially", người đọc có thể overread mức khách quan của test
(proposed by codex, `codex/round-2_reviewer-reply.md:113-114`).

**§7(b) — Why it does not stand**: D4 already requires structured derivation artifact.
The gap is not architectural but spec-level: mandating that "Partially" results include
a prose justification artifact documenting data-derived portions. This is implementable
within the agreed architecture without changing the test design.
(`claude_code/round-2_author-reply.md:231-238`).

**Remaining tradeoff**: "Partially" artifact requirement adds review overhead per rule.
Without it, test objectivity is overestimated. Overhead is bounded (v1 seeds ~25 rules,
not thousands).

**Classification**: Judgment call (§14, near-convergence).
**Decision_owner**: Human researcher.

---

### X38-MK-07 — F-06 Whitelist Reconciliation

**Substantive agreement** (round 2): Both sides agree: (1) F-06 = content filter,
tier = governance filter — two orthogonal dimensions; (2) dropping F-06 gate was a
non sequitur; (3) category vocabulary may need refinement but the gate stays.

**§7(a) — Steel-man of author's old position**: Nếu F-06 category vocabulary không
được sharpen hoặc rename rõ, người triển khai có thể force-fit các rule
audit/methodology mới vào bucket sai, tái tạo ambiguity ngay trong content gate
(proposed by codex, `codex/round-2_reviewer-reply.md:132-133`).

**§7(b) — Why it does not stand**: Vocabulary refinement is implementation work on
an agreed architecture, not an architectural dispute. The reconciliation (F-06 ⊥ tier)
is stable regardless of vocabulary labels. Sharpening vocabulary belongs to topic 002
(contamination firewall), which owns the content gate.
(`claude_code/round-2_author-reply.md:274-281`).

**Remaining tradeoff**: Unsharpened vocabulary creates ambiguity at implementation
time. But sharpening vocabulary before topic 002 debate completes risks premature
commitment to categories that the firewall design may reshape.

**Classification**: Judgment call (§14, near-convergence).
**Decision_owner**: Human researcher.

---

### C1 — Policy Compiler Boundary

**Substantive agreement** (round 2): Both sides agree: (1) compiler = deterministic
constraint validator (not "format validator ONLY"); (2) compiler does NOT auto-promote
to Tier 1 — human gate exists; (3) compiler MUST NOT claim epistemological
classification; (4) boundary between deterministic checks and semantic review needs
explicit documentation.

**§7(a) — Steel-man of author's old position**: Dù compiler không auto-promote Tier 1,
nếu giao diện/artefact của compiler không tách rõ "constraint PASS" khỏi "semantic
review pending", người vận hành vẫn có thể hiểu nhầm PASS là epistemic approval và
tạo false sense of safety
(proposed by codex, `codex/round-2_reviewer-reply.md:151-152`).

**§7(b) — Why it does not stand**: The boundary table in
`claude_code/round-2_author-reply.md:312-318` explicitly separates compiler outputs
(format, scope ≤ provenance, category ∈ whitelist, required metadata, overlap guard)
from classification outputs (tier, basis, leakage grade, force, challenge quality).
MK-08's 3-axis model (Stage 1B) reinforces this: `constraint_status` is a separate
axis from `lifecycle_state`. Compiler produces `constraint_status = PASSED`, not
lifecycle advancement. The artifact design should include `semantic_status: PENDING`
alongside `constraint_status: PASSED` to prevent misreading.

**Remaining tradeoff**: Additional field in compiler output adds minor complexity.
Without it, operators may conflate constraint pass with full approval.

**Classification**: Judgment call (§14, near-convergence).
**Decision_owner**: Human researcher.

---

### C2 — Auditor Agent Bounded Authority

**Substantive agreement** (round 2): Both sides agree: (1) auditor role stays in
architecture, bounded by asymmetric authority (downgrade/narrow only); (2) adversarial
probing is a procedural variant under the same final human authority, not a structural
fix for circularity; (3) auditor criteria need specification as reviewable artifact;
(4) v1 = shadow-only, audit mechanics not active.

**§7(a) — Steel-man of author's old position**: Bounded authority chỉ giảm blast
radius, không tự tạo legitimacy; nếu tiêu chí downgrade/narrow không được spec thành
artifact reviewable, auditor vẫn có thể vận hành tùy tiện và âm thầm bóp nghẹt
useful priors
(proposed by codex, `codex/round-2_reviewer-reply.md:170-171`).

**§7(b) — Why it does not stand**: D9 (from Topic 000) already mandates reviewable
auditor criteria. The auditor role is architecturally justified by asymmetric authority
and human final gate. The remaining work (specifying WHAT the criteria are) depends on
MK-08 lifecycle states and is a downstream design task, not an architectural objection
to the auditor's existence. (`claude_code/round-2_author-reply.md:351-358`).

**Remaining tradeoff**: Criteria schema frozen for v1 (see Addendum C2); calibration
and threshold tuning deferred to v2+. Risk: v2+ deploys auditor without calibrated
thresholds. Mitigation: D9 obligation carries forward; minimal schema provides
structural guardrails.

**Classification**: Judgment call (§14, near-convergence).
**Decision_owner**: Human researcher.

---

## Key Architectural Decisions

### Decided (Converged)

| ID | Decision | Evidence |
|----|----------|----------|
| MK-01 | Alpha-Lab formalizes explicit rule transitions; no implicit absorption | V4→V8 absorption ≠ convergence (`CONVERGENCE_STATUS_V3.md:5-10` [extra-archive]) |
| MK-02 | Harm #3 (implicit data leakage) is irreducible in useful operating region; mitigations bound it, cannot eliminate | Tier-1-only eliminates leakage but also learning (`findings-under-review.md:163-174`) |
| MK-05 | 3 tiers (axiom, structural prior, session-scoped); metadata handles Tier 2 breadth | Adding boundaries adds classification cost without enforcement gain |
| MK-06 | 3 leakage types (parameter, structural, attention); enforcement vocabulary for implementation | Binary model fails on V8 "transported clone" middle ground |
| MK-08 | 3-axis lifecycle: `constraint_status` / `semantic_status` / `lifecycle_state`. `RETIRED → PROPOSED` for re-entry (full pipeline) | D8 content gates ⊥ governance states; D1 requires re-registration |
| MK-09 | Challenge process = v2+ design. V1 records challenge observations only | MK-17 shadow-only eliminates v1 runtime need |
| MK-10 | Expiry = v2+ design. V1 lifecycle includes `REVIEW_REQUIRED` as trigger target | D1 forbids silent retirement; primitives undefined for v1 |
| MK-11 | Conflict resolution = v2+ (requires D3 context schema first). Ranking ≠ conflict semantics | No active empirical priors in v1 |
| MK-12 | Epistemic states qualitative; numeric knobs are operational defaults only | Scalar confidence = stealth confidence without independence guarantees |
| MK-13 | `transitions/` = canonical source of truth. `registry.json` = materialized view. Artifacts versioned per `transition_id` | D1 auditability; no singleton overwrite |
| MK-14 | Topic 002 owns content gate (`ADMISSIBLE/BLOCKED`); Topic 004 owns lifecycle gate. No overlap | D7 single-ownership; interface decomposition |
| MK-15 | Bootstrap: classify V4→V8 lessons via derivation test, tag provenance, all Tier 2 = `SHADOW` per MK-17. No LEGACY tier | MK-17 separates seeding from influence; 3-tier taxonomy (D5) |
| MK-16 | Ratchet risk mitigations converged (v2+ design) | Pre-debate convergence |
| MK-17 | Same-dataset empirical priors = shadow-only pre-freeze | Root question; x37 evidence (`CONVERGENCE_STATUS_V3.md:138-145` [extra-archive]) |
| C3 | Budget split = v2+ design. V1: all search is frontier | No frontier/probe in v1 shadow-only |
| C4 | Superseded by MK-17; overlap guard trivially resolved | Same-dataset = all shadow |
| C5 | Active cap = v2+ (requires D3 + MK-11 conflict model first) | Attention management ≠ conflict resolution |
| C6 | Stage runtime aggressively; freeze governance invariants now (D1/D4/D5/D7/D8/D9) | MK-17 eliminates v1 runtime value |

### Deferred to Human Researcher (Judgment Call, §14)

| ID | Agreed direction | Open spec question | Recommendation |
|----|------------------|--------------------|----------------|
| MK-03 | Operating point = f(context), not constant. MK-17 = first boundary | How to constrain v2+ context declaration | Record minimum requirement: dataset identity + contamination lineage |
| MK-04 | Derivation test = admissibility lens. Human-performed. Force in governance layer | "Partially" result artifact format | Mandate prose justification for data-derived portions |
| MK-07 | F-06 ⊥ tier (content filter vs governance filter). Gate stays | Category vocabulary sharpening | Defer to topic 002. **AMENDED 2026-03-23**: interim rule revised (GAP ≠ AMBIGUITY). See addendum |
| C1 | Compiler = deterministic constraint validator. No epistemic claims | Artifact must show `semantic_status: PENDING` alongside `constraint_status: PASSED` | Add field to compiler output spec |
| C2 | Auditor stays with asymmetric authority (downgrade/narrow only) | Criteria specification as reviewable artifact | D9 obligation carries forward; spec criteria when MK-08 lifecycle is implemented |

---

## V1 Frozen Governance Invariants

Per C6 convergence, these MUST be frozen for v1 (not deferred):

1. **D1**: Explicit, reversible, auditable transitions
2. **D4**: Structured derivation artifact
3. **D5**: 3-tier taxonomy
4. **D7**: Content gate / F-06 single ownership (topic 002)
5. **D8**: Compiler constraint validation (deterministic)
6. **D9**: Auditor reviewable criteria
7. **MK-08**: Lifecycle state machine (3-axis)
8. **MK-13**: Storage law (transitions canonical, registry materialized)
9. **MK-17**: Same-dataset empirical priors = shadow-only

---

## V1 Storage Structure (MK-13 Converged Design)

```
knowledge/
├── registry.json              ← materialized view (NOT source of truth)
├── transitions/               ← canonical source of truth (append-only)
│   └── {timestamp}_{rule_id}_{from}_{to}.json
├── artifacts/                 ← versioned per transition
│   └── {rule_id}/
│       └── {transition_id}/
│           ├── constraint_validation.json    (D8)
│           ├── semantic_review.json          (D8)
│           ├── derivation_test.json          (D4)
│           └── auditor_assessment.json       (D9)
└── audit/                     ← free-text, not in runtime payload
    └── {rule_id}/
        └── provenance.md
```

---

## V1 Lifecycle State Machine (MK-08 Converged Design)

```
Three independent axes:

constraint_status:  PENDING → PASSED | FAILED
semantic_status:    PENDING → REVIEWED | REJECTED
lifecycle_state:    PROPOSED → REGISTERED → ACTIVE | SHADOW | SESSION_SCOPED
                                            ↓                    ↓
                                     REVIEW_REQUIRED       (auto-expire)
                                            ↓
                                         RETIRED
                                            ↓
                                         PROPOSED (re-entry, full pipeline)

Gate: PROPOSED → REGISTERED requires constraint=PASSED AND semantic=REVIEWED
```

---

## Complete Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Resolved in |
|----------|-------|-----------|------------|-------------|
| X38-MK-01 | Maturity pipeline | Thiếu sót | **Converged** | Stage 1A, R2 |
| X38-MK-02 | Five harms | Sai thiết kế | **Converged** | Stage 1A, R2 |
| X38-MK-03 | Fundamental constraint | Judgment call | **Judgment call** | §14 → human researcher (see Addendum) |
| X38-MK-04 | Derivation test | Thiếu sót | **Judgment call** | §14 → human researcher (see Addendum) |
| X38-MK-05 | 3-Tier taxonomy | Thiếu sót | **Converged** | Stage 1A, R2 |
| X38-MK-06 | Three leakage types | Thiếu sót | **Converged** | Stage 1A, R2 |
| X38-MK-07 | F-06 whitelist | Thiếu sót | **Judgment call (AMENDED 2026-03-23, RESOLVED 2026-03-25)** | §14 → human researcher (see Addendum). GAP ≠ AMBIGUITY permanent. Topic 002 chose second fork: no category expansion, `UNMAPPED` permanent |
| X38-MK-08 | Lesson lifecycle | Thiếu sót | **Converged** | Stage 1B, R6 |
| X38-MK-09 | Challenge process | Thiếu sót | **Converged** | Stage 1B, R5 |
| X38-MK-10 | Expiry mechanism | Thiếu sót | **Converged** | Stage 1B, R5 |
| X38-MK-11 | Conflict resolution | Thiếu sót | **Converged** | Stage 1B, R5 |
| X38-MK-12 | Confidence scoring | Judgment call | **Converged** | Stage 1B, R5 |
| X38-MK-13 | Storage format | Judgment call | **Converged** | Stage 1B, R6 |
| X38-MK-14 | Firewall boundary | Thiếu sót | **Converged** | Stage 1B, R5 |
| X38-MK-15 | Bootstrap problem | Judgment call | **Converged** | Stage 1B, R5 |
| X38-MK-16 | Ratchet risk | Sai thiết kế | **Converged (pre-debate)** | Pre-debate |
| X38-MK-17 | Central question | Judgment call | **RESOLVED** | Pre-debate |
| C1 | Compiler boundary | Thiếu sót | **Judgment call** | §14 → human researcher (see Addendum) |
| C2 | Auditor authority | Thiếu sót | **Judgment call** | §14 → human researcher (see Addendum) |
| C3 | Budget split | Thiếu sót | **Converged** | Stage 1B, R5 |
| C4 | Overlap guard | Sai thiết kế | **Converged (superseded by MK-17)** | Stage 1B, R5 |
| C5 | Active cap | Thiếu sót | **Converged** | Stage 1B, R5 |
| C6 | V1 complexity scope | Thiếu sót | **Converged** | Stage 1B, R5 |

---

## Addendum: Human Researcher Judgment-Call Decisions (2026-03-21)

**Decision owner**: Human researcher (per §15).
**Decision criteria**: bám triết lý lõi, giảm silent leakage, giữ reversibility,
không nhồi complexity vô ích vào v1 same-dataset, tôn trọng single ownership.

**Epistemological note**: Debate converged directions. Decisions below tighten spec
details within those directions. These are "judgment-call tightening for draft/spec",
not "repo already converged to those exact fields/enums." Distinction matters for
downstream drafting.

**Full deliberation record**: `judgment-call-deliberation.md` — contains original
proposals, claude_code assessment, codex corrections (MK-07 + C2), and reasoning chain.

### MK-03 — Accept + Strengthen

Direction accepted: operating point = f(context), not constant. MK-17 = first boundary.

**Decision**: Freeze minimum context manifest for v2+. Campaign MUST declare:
- `dataset_identity`
- `overlap_class`: exact_same | appended | partial_overlap | disjoint
- `contamination_lineage`

Missing manifest → all Tier 2/3 empirical priors default to SHADOW.

`overlap_class` enum is decision-owner addition (not debate-converged). Broader
campaign-context schema (campaign/dataset/asset/data_surface/objective/execution/
date_range dimensions from proposal) NOT frozen — insufficient evidence to spec.

### MK-04 — Accept + Strengthen

Direction accepted: derivation test = admissibility lens, human-performed,
"Partially" requires judgment. D4 + `derivation_test.json` already v1 invariant/artifact.

**Decision**: "Partially" verdict INVALID without structured artifact containing
at minimum:
- `first_principles_core` — what portion is derivable from first principles
- `empirical_residue` — what portion is data-derived
- `admissibility_rationale` — why rule is still admissible despite data residue
- `reviewer` — who performed the test
- `timestamp`

No artifact, no Partially. Exact field names are decision-owner spec (not
debate-converged).

### MK-07 — Accept Defer + Interim Rule (AMENDED 2026-03-23)

Direction accepted: F-06 ⊥ tier. Gate stays. Vocabulary ownership = Topic 002.

**Original decision (2026-03-21)**: Defer vocabulary sharpening to Topic 002.
Interim rule: ambiguous category mapping → non-admissible pending human review.
No force-fitting by implementers into nearest bucket.

No new state name frozen (e.g., NOT freezing "BLOCKED_PENDING_REVIEW" — that would
create vocabulary in a topic that deferred vocabulary ownership).

**Amendment (2026-03-23) — known problem + revised interim rule**:

Post-closure investigation tested the 4 F-06 categories against ~75 actual
V4-V8 rules. Results: ~60 clean fit, ~10 GAP (no category fits), ~5 ambiguous.
Full report: `../002-contamination-firewall/input_f06_category_coverage.md`.

The gap rules are all **Tier 2 structural priors** — empirical observations
elevated to methodology (MK-02 Harm #3 "information laundering"). Examples:
V5-3 "slower context + faster persistence complement", V6-2/T2-1 "layering is
hypothesis", T2-2 "microstructure excluded from swing horizon", CS-6 "complexity
not proven stable superior".

**Problem with original interim rule**: "ambiguous → non-admissible" blocks
structural priors that SHOULD be admitted with Tier 2 + SHADOW governance
(per MK-17). An implementer encountering a gap rule cannot resolve it — no
category to assign, force-fitting prohibited, rule stuck in limbo. The
fail-closed assumption (unmappable = probably contamination) is wrong for this
class of rules.

**Revised interim rule** (distinguishes GAP from AMBIGUITY):

- **AMBIGUITY** (rule plausibly maps to multiple categories): non-admissible
  pending human review. Fail-closed is correct here — the rule IS within F-06's
  scope, the question is which category.
- **GAP** (rule fits no category without stretching): admit provisionally with
  explicit `category: UNMAPPED` tag + mandatory Tier 2 + SHADOW (per MK-17).
  Flag for Topic 002 category expansion. Do NOT block — these rules contain
  real methodology content, not answer priors. Blocking them loses knowledge
  that the governance system (tier + shadow) is designed to handle safely.

**Constraint preserved**: no new F-06 category name frozen by Topic 004.
`UNMAPPED` is a governance tag (Topic 004 territory — "what to do when
vocabulary is insufficient"), not a content category (Topic 002 territory —
"what the vocabulary contains"). Same distinction as D7.

**Final fix resolved by Topic 002 (CLOSED 2026-03-25)**: Topic 002 declined
category expansion. `UNMAPPED` + Tier 2 + SHADOW is now the **permanent**
governance path for this class of rules. The `UNMAPPED` tag does NOT retire in v1.
4 F-06 whitelist categories unchanged. See
`../002-contamination-firewall/final-resolution.md` §Decision 4, §Decision 5.

### C1 — Accept Exactly

Direction accepted: compiler = deterministic constraint validator, no epistemic claims.

**Decision**: Compiler output artifact MUST include `semantic_status: PENDING`
alongside `constraint_status: PASSED`. Non-negotiable per MK-08 3-axis model.
Any artifact/UI showing "PASS" without "semantic review pending" is spec-incorrect.

### C2 — Accept + Substantive Correction

Direction accepted: auditor stays, asymmetric authority (downgrade/narrow only),
human final gate.

**Correction**: final-resolution.md simultaneously freezes D9 (v1 invariant),
includes `auditor_assessment.json` in storage law, but defers criteria spec entirely.
These three positions are incompatible. Fix: freeze criteria SCHEMA now, defer
calibration/thresholds.

**Decision**: Freeze minimal auditor artifact schema:
- `ground_code` — reason for action
- `evidence_refs` — pointers to evidence
- `proposed_action` — downgrade | narrow
- `scope_change` — what changes
- `human_review_required` — boolean
- `notes` — free text

Initial ground_code value set (provisional, NOT closed law):
SCOPE_MISMATCH, DERIVATION_WEAKNESS, CATEGORY_AMBIGUITY, CONTAMINATION_RISK,
HIGHER_TIER_CONFLICT.

Ground set is initial/provisional because: (a) not debate-proven, (b) some values
(CONTAMINATION_RISK, CATEGORY_AMBIGUITY) touch Topic 002 firewall semantics.
Can be refined during drafting. Schema structure IS frozen.

Note: HIGHER_TIER_CONFLICT ground exists but v1 conflict resolution = always human
(MK-11 deferred to v2+). No machine resolution path in v1.

---

**Topic 004 — CLOSED. Decisions signed off by human researcher.**
