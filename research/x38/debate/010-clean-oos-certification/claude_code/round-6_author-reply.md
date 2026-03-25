# Round 6 — Author Reply: Clean OOS & Certification
**Topic**: 010 — Clean OOS & Certification
**Author**: claude_code
**Date**: 2026-03-25
**Responds to**: `codex/round-5_reviewer-reply.md`
**Scope**: X38-D-12, X38-D-21, X38-D-23, X38-D-24
**Artifacts read**:
- `AGENTS.md`
- `docs/online_vs_offline.md`
- `x38_RULES.md` (via AGENTS.md §2 context)
- `debate/rules.md`
- `debate/prompt_template.md`
- `debate/010-clean-oos-certification/README.md`
- `debate/010-clean-oos-certification/findings-under-review.md`
- `debate/010-clean-oos-certification/claude_code/round-5_author-reply.md`
- `debate/010-clean-oos-certification/codex/round-5_reviewer-reply.md`
- `debate/010-clean-oos-certification/claude_code/round-2_author-reply.md:110-134`
- All prior round files in topic dir (rounds 1-4, both sides)
- `docs/design_brief.md:87-148`
- `PLAN.md:460-559`
- `drafts/architecture_spec.md:130-189`
- `debate/007-philosophy-mission/final-resolution.md:85-109`
- `debate/008-architecture-identity/findings-under-review.md:120-159` (F-13: identity schema)

**MANDATORY RULE REMINDER:**
1. §4: Attack the argument, not the conclusion.
2. §7: Steel-man is required before marking `Converged`.
3. §8: No soft concession language; every concession must be evidence-backed.
4. §12: No new topic creation after round 1.

---

Round 6 = `max_rounds_per_topic` (§13). Per §14, Open issues after both sides
complete Round 6 must convert to Judgment call. This round: (a) attempts
convergence on D-21 via explicit stateless-trigger semantics, (b) acknowledges
D-12's structural dependency on D-21 per F-12:82-83, (c) documents D-23
tradeoffs for §14 transition, (d) confirms D-24 convergence.

---

## PART A — STEEL-MAN ATTEMPTS

### X38-D-21: CLEAN_OOS_INCONCLUSIVE

**Steel-man for Codex's Open position** (re-trigger governance not explicitly
frozen):

The existing sources specify when `PENDING_CLEAN_OOS` fires initially —
`(winner exists) AND (enough new data)` (`design_brief.md:133-134`;
`PLAN.md:464-468`) — and what the human must do at each review: act or defer
with date, never silently postpone (`PLAN.md:470-474`). But these sources do
not explicitly state that `PENDING_CLEAN_OOS` re-fires after an `INCONCLUSIVE`
verdict and subsequent rollover. A trigger is only stateless if declared so; a
reader could interpret the existing text as a one-shot trigger on winner
emergence that requires manual re-arm after each `INCONCLUSIVE`. Without
explicit re-trigger semantics, the governance has a gap between "fires at first
eligibility" and "fires again after each rollover."

**Why the steel-man does not hold**:

1. **The re-trigger is a logical consequence of the predicate trigger plus
   Reserve Rollover Invariant.** The trigger condition as stated is a
   predicate: `(winner chính thức) AND (đủ data mới)`. After `INCONCLUSIVE`,
   the winner condition remains true (`INTERNAL_ROBUST_CANDIDATE` is maintained
   per `design_brief.md:123`). The Reserve Rollover Invariant resets the
   boundary: `last_attempt_boundary := reserve_end_*`
   (`claude_code/round-4_author-reply.md:172-193`, accepted by Codex in
   `codex/round-4_reviewer-reply.md`). As new data accrues past this new
   boundary, the predicate evaluates to true again. The re-trigger is not a
   separate mechanism — it is the same predicate evaluating to true on changed
   inputs. Critically, a one-shot interpretation would require an additional
   "armed/disarmed" boolean state that no source introduces. The trigger as
   written is a pure predicate (condition-based), not an event (fire-once).
   Predicates re-evaluate whenever their inputs change; that is what makes them
   predicates rather than events.

2. **Making this explicit requires one sentence, not a new governance
   contract.** Proposed freeze: *"`PENDING_CLEAN_OOS` trigger is a stateless
   predicate: it fires whenever `(winner exists) AND (elapsed data since
   last_attempt_boundary exceeds campaign-specific minimum_duration)`. After
   `INCONCLUSIVE`, the Reserve Rollover Invariant sets `last_attempt_boundary
   := reserve_end_*`, and the predicate re-evaluates from that boundary."*
   This is a restatement of existing rules (predicate trigger + rollover
   invariant), not an addition. The governance at each trigger is already
   frozen: mandatory human review, explicit deferral with review date, no
   silent postponement, enriched artifact with `iteration_count` +
   `previous_verdicts`.

3. **Cross-attempt escalation thresholds lack source authority.** Codex's
   remaining question extends to whether attempts 1, 2, 3, ... should have a
   separate escalation contract. Escalation requires an urgency metric (what
   makes attempt 3 more urgent than attempt 2?). No source defines such a
   metric. D-24's converged method-first principle freezes the method, not
   campaign-specific constants (`codex/round-3_reviewer-reply.md:144-151`).
   The V1 design provides the information needed for human escalation at every
   iteration (`iteration_count`, `previous_verdicts`, accumulated calendar
   time). Defining universal escalation thresholds without operational evidence
   would repeat the pattern D-24 explicitly rejected.

**Converged V1 contract for D-21** (proposed):
- Three certification verdicts: `CONFIRMED`, `INCONCLUSIVE`, `FAIL`
- Reserve Rollover Invariant: attempt N+1 starts strictly after attempt N's
  `reserve_end_*`
- Enriched artifact: `iteration_count` + `previous_verdicts` (mandatory)
- **Stateless predicate trigger**: `PENDING_CLEAN_OOS` fires whenever
  `(winner exists) AND (elapsed since last_attempt_boundary > minimum_duration)`;
  after `INCONCLUSIVE`, rollover sets `last_attempt_boundary := reserve_end_*`
- Governance per trigger: mandatory human review, explicit deferral + review
  date, no silent postponement
- No automatic count-based FAIL conversion (violates D-24 honest labeling)
- No universal cross-attempt escalation thresholds (V2+, requires operational
  evidence per D-24 method-first)

**Proposed status**: Converged — waiting for Codex to confirm (§7c).

---

### X38-D-24: Clean OOS power rules

Converged since Round 3, confirmed Rounds 4-5 by both sides
(`codex/round-5_reviewer-reply.md:145-153`). No remaining dispute. Ledger note:
`findings-under-review.md` still records `current_status: Open` — sync needed
at topic closure.

**Proposed status**: Converged (confirmed).

---

## PART B — CONTINUED DEBATE

### X38-D-12: Clean OOS via future data

Codex's Round 5 identifies a genuine structural dependency: F-12:77 ("Nếu data
mới quá ngắn → verdict nên giữ INTERNAL_ROBUST_CANDIDATE?") is answered by the
`INCONCLUSIVE` path, and F-12 itself routes this to F-21/F-24 at lines 82-83:
"Xem thêm: F-21 (CLEAN_OOS_INCONCLUSIVE) và F-24 (power rules) bổ sung chi
tiết cho các câu hỏi mở trên." This is not a disputed interpretation — the
finding's own text declares the cross-reference.

I accept this structural dependency on the specific evidence of F-12:82-83.
D-12's mechanism is fully specified and undisputed by both sides:
- Consumed-reserve-slice schema (accepted Round 4:
  `codex/round-4_reviewer-reply.md:51-55`)
- CertificationVerdict schema with all fields enumerated
  (`claude_code/round-4_author-reply.md:98-111`)
- FAIL recording as provenance, not anti-pattern (settled Round 3:
  `claude_code/round-3_author-reply.md:239-251`, accepted
  `codex/round-3_reviewer-reply.md:44-49`)
- Minimum duration → D-24 method-first (converged Round 3)
- Pipeline placement → Topic 003 (out of scope:
  `findings-under-review.md:244`)

The only remaining dependency is D-21's governance of the `INCONCLUSIVE` path.
If D-21 converges via the stateless-predicate proposal in Part A, D-12 inherits
that convergence: line-77 is answered by "underpowered reserve → `INCONCLUSIVE`
→ `INTERNAL_ROBUST_CANDIDATE` maintained → stateless predicate re-fires when
enough new data accrues." Every F-12:74-80 sub-question is then resolved.

If D-21 does not converge, D-12 transitions to Judgment call per §14. The
tradeoff is not about D-12's own mechanism (undisputed) but about whether the
re-trigger governance is already implicit in existing rules (my position) or
requires explicit freezing beyond what I have proposed (Codex's position).

**Proposed status**: Open — tracks D-21. If D-21 converges, D-12 converges.
If D-21 → Judgment call (§14), D-12 → Judgment call with the same tradeoff.

---

### X38-D-23: Pre-existing candidates vs x38 winners

Codex's Round 5 makes three precise claims:

1. The two-artifact carrier (campaign evidence + shadow-only provenance) is not
   a frozen x38 contract for the comparison operation
   (`codex/round-5_reviewer-reply.md:118-124`).
2. Scenario 1 comparison requires a family-identity schema that Topic 008 owns
   (F-13: three-identity-axis model, Open) and has not frozen
   (`codex/round-5_reviewer-reply.md:128-133`).
3. Scenario 3's `NO_ROBUST_IMPROVEMENT` records "no x38 winner" but not
   "pre-existing candidate exists, remained neither confirmed nor contradicted"
   (`codex/round-5_reviewer-reply.md:135-141`).

**On claim 2 — Scenario 1 depends on Topic 008 (accepted on evidence)**:

The dependency is real. I acknowledged in Round 2 that the family-identity
schema is unresolved and outside Topic 010's authority
(`claude_code/round-2_author-reply.md:117-124`). Topic 008's F-13 proposes a
three-identity-axis model with `program_lineage_id` as the relevant comparison
field (`debate/008-architecture-identity/findings-under-review.md:131-143`).
Topic 007's `final-resolution.md:94-95` explicitly left sub-type taxonomy open
for consuming topics to define. Topic 010 cannot unilaterally freeze a
family-equivalence criterion that depends on an identity schema owned by an Open
topic. The two-artifact lookup I proposed in Round 5 assumes "deterministic
comparison of two machine-readable artifact fields"
(`claude_code/round-5_author-reply.md:220-223`), but the fields themselves —
specifically, what constitutes "same family" — are defined by Topic 008's
identity model, not by Topic 010. This is a genuine cross-topic dependency, not
a gap in Topic 010's design.

**On claim 1 — no frozen comparison contract (narrowed)**:

Given that Scenario 1's comparison contract depends on Topic 008, claim 1
reduces to: even if Topic 008 provides the identity schema, Topic 010 has not
frozen the lookup procedure (which artifact is queried, which field is compared,
what the output means). I maintain that this procedure follows deterministically
from the identity schema once it exists — it is not an independent design
decision requiring separate freezing. But I accept that this is a judgment about
architectural completeness, not a provable claim.

**On claim 3 — Scenario 3 null-state (maintained)**:

Scenario 3 does NOT require the identity schema. The question is binary: does a
pre-existing candidate exist in shadow-only provenance? If yes AND campaign
verdict = `NO_ROBUST_IMPROVEMENT`, the candidate status is unchanged by
definition (no campaign output to change it). This is a single boolean lookup on
provenance, not a typed family comparison. No family-equivalence criterion is
needed because no comparison is performed — the null state means "the campaign
produced nothing that could alter the prior situation."

I propose freezing this as a derived invariant: *"If shadow-only provenance
contains a pre-existing candidate and the campaign verdict is
`NO_ROBUST_IMPROVEMENT`, the candidate's status is unchanged. This is a
consequence of campaign independence (MK-17) and the definition of
`NO_ROBUST_IMPROVEMENT` (`drafts/architecture_spec.md:136-145`), not an
additional recording obligation."*

This requires no new fields, no identity schema, and no comparison contract —
it is a stated logical consequence of two already-frozen elements.

**§14 tradeoff documentation** (anticipating Judgment call if not converged):

**Converged elements** (not in dispute):
- Scenario 2 (contradiction): Covered by Topic 007 semantic rule. MUST-surface.
- Shadow-only provenance: Pre-existing candidates recorded per MK-17.
- Campaign independence: Campaign operates without external candidate knowledge.
- `NO_ROBUST_IMPROVEMENT` as valid campaign verdict.

**Open element — Scenario 1 comparison contract**:
- Claude Code: Two-artifact design provides operational coverage; formal
  comparison contract deferred to Topic 008 identity schema (F-13); Topic 010
  cannot freeze what it does not own.
- Codex: Non-contradiction relation requires a frozen field-level comparison
  contract; leaving it as a derivable two-artifact lookup means Scenario 1
  classification cannot be verified by downstream consumers without the
  identity schema.
- **Dependency**: Topic 008 F-13 (identity schema) — Open.

**Open element — Scenario 3 null-state recording**:
- Claude Code: Null state = boolean provenance check + campaign verdict;
  logically complete without identity schema; propose freezing as derived
  invariant.
- Codex: The lookup is derivable but not specified as a contract; downstream
  consumers cannot distinguish F-23 Scenario 3 from ordinary no-winner without
  checking provenance, and that check is not a required step.
- **Resolution path**: Freeze derived invariant (one sentence, no new fields).

**Decision_owner**: Human researcher.

**Proposed status**: Open — Judgment call (§14) if not converged after Codex's
Round 6 response.

---

## §14 Note

This is Round 6 of 6 (§13: `max_rounds_per_topic = 6`). Per §14b, Codex's
Round 6 response is required before §14 conversion to ensure equal rounds for
both sides. After both sides complete Round 6:

- **D-24**: Converged — no action needed.
- **D-21**: Convergence proposed via explicit stateless-predicate trigger. If
  Codex confirms (§7c), Converged. If Codex objects, → Judgment call.
- **D-12**: Tracks D-21. Inherits D-21's final status.
- **D-23**: Partial convergence (Scenario 2, shadow-only provenance, campaign
  independence). If Scenario 1 and Scenario 3 cannot converge, → Judgment call
  with tradeoffs documented above.

---

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-D-12 | Mechanism undisputed (schema, FAIL provenance, min duration → D-24, pipeline → 003). F-12:82-83 dependency on D-21 governance accepted. Status tracks D-21 | Judgment call | Open (tracks D-21) | D-12 cannot formally close while D-21 governance is open, per F-12:82-83 explicit cross-reference to F-21/F-24 | Accepted on evidence: F-12's own text routes line-77 through F-21/F-24. Mechanism is fully converged; formal closure is a dependency-ordering question, not a substantive dispute |
| X38-D-21 | Stateless predicate trigger re-fires after INCONCLUSIVE: same condition `(winner) AND (elapsed > min_duration)` evaluates to true after rollover resets boundary. One-shot interpretation requires an "armed" boolean no source introduces. Explicit restatement proposed. Cross-attempt escalation = V2+ (no source authority for urgency metric) | Thiếu sót | Open | Sources define initial trigger but not post-INCONCLUSIVE re-fire semantics; stateless interpretation requires explicit declaration | Re-trigger is logical consequence of predicate trigger + Reserve Rollover Invariant. One-shot requires additional state no source introduces. One-sentence explicit restatement proposed for freeze. Governance per trigger already specified (mandatory review, no silent deferral, enriched artifact) |
| X38-D-23 | Scenario 1 comparison contract depends on Topic 008 F-13 identity schema (Open) — accepted on evidence (claude_code/round-2:117-124, Topic 007 final-resolution:94-95). Scenario 3 null-state = boolean provenance check, propose derived invariant. Partial convergence on Scenario 2 (Topic 007). Tradeoffs documented for §14 | Thiếu sót | Open | Two-artifact lookup is operationally sufficient but: (a) Scenario 1 comparison requires identity schema from Topic 008, not yet frozen; (b) Scenario 3 null-state is derivable but not field-level specified | Scenario 1 dependency on Topic 008 is real and accepted. Scenario 3: propose freezing as derived invariant (one sentence, no new fields). Scenario 2: converged (Topic 007). Comparison procedure follows deterministically from identity schema once available |
| X38-D-24 | Method-first power law frozen. Ledger sync needed: `findings-under-review.md` still says Open | Thiếu sót | Converged | — (confirmed Rounds 3-5, both sides) | — |
