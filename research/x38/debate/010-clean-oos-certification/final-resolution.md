# Final Resolution — Clean OOS & Certification

**Topic ID**: X38-T-10
**Closed**: 2026-03-25
**Rounds**: 6
**Participants**: claude_code, codex

---

## Decisions

| Issue ID | Finding | Resolution | Type | Round closed |
|----------|---------|------------|------|-------------|
| X38-D-12 | Clean OOS via future data | Accepted — consumed-reserve-slice schema, CertificationVerdict fields, auto-trigger governance, FAIL-as-provenance. Closure inherited from D-21 rerun governance (F-12:82-83 dependency). | Converged | 6 |
| X38-D-21 | CLEAN_OOS_INCONCLUSIVE — first-class verdict state | Accepted — three verdicts (CONFIRMED/INCONCLUSIVE/FAIL), Reserve Rollover Invariant, stateless predicate trigger with explicit post-INCONCLUSIVE re-fire, enriched artifact, mandatory human review per trigger. | Converged | 6 |
| X38-D-23 | Pre-existing candidates vs x38 winners | Accepted (Claude Code position) — Scenario 1 deferred to Topic 008 identity schema; Scenario 2 covered by Topic 007 semantic rule; Scenario 3 frozen as derived invariant. | Judgment call | 6 |
| X38-D-24 | Clean OOS power rules | Accepted — method-first: predeclared campaign-specific power method, mandatory calendar-time and trade-count criteria, honest INCONCLUSIVE when underpowered. No universal gate set. | Converged | 3 (confirmed rounds 4-6) |

## Round symmetry

Both agents completed 6 rounds each (claude_code: rounds 1-6, codex: rounds 1-6).
No asymmetry to document per §14b.

---

## Key design decisions (for drafts/)

### Decision 1: Clean OOS Protocol — Phase 2 Lifecycle

**Accepted position**: Clean OOS is Phase 2 after research, not a campaign type.
Lifecycle: research (Phase 1) → wait for new data → Clean OOS replay (Phase 2)
→ CONFIRMED / INCONCLUSIVE / FAIL → if FAIL, Phase 3 (new research on expanded
data).

**Key elements**:
- Clean reserve = genuinely new data only (not internal holdout)
- One-shot reserve law with executable timestamp boundaries (bar `close_time`,
  per-timeframe)
- CertificationVerdict schema: `frozen_spec_ref`, `reserve_boundary_*`,
  `reserve_end_*`, `append_data_ref`, `verdict`, `metrics`, `iteration_count`,
  `previous_verdicts`
- FAIL lineage: immutable record in CertificationVerdict, historical
  evidence/provenance, NOT anti-pattern (no MetaLesson pipeline interaction)
- Module placement: deferred to Topic 003 (pipeline structure)

**Rejected alternative**: Clean OOS as a parallel campaign type running
alongside research campaigns.

**Rationale**: `findings-under-review.md:29-41` (lifecycle), `design_brief.md:120-145`
(Phase 2 definition), `PLAN.md:519-539` (implementation).
Round 4 schema acceptance: `codex/round-4_reviewer-reply.md:51-55`.

### Decision 2: Auto-Trigger Governance (PENDING_CLEAN_OOS)

**Accepted position**: Framework auto-creates `PENDING_CLEAN_OOS` obligation when
`(winner exists) AND (enough new data)`. Stateless predicate trigger — re-fires
after each INCONCLUSIVE via Reserve Rollover Invariant.

**Governance per trigger**:
- Human researcher must act or explicitly defer with review date
- No silent indefinite deferral (violation)
- Enriched artifact: `iteration_count` + `previous_verdicts` (mandatory fields)
- Human researcher = escalation authority at every iteration

**Rejected alternative**: Automatic count-based FAIL conversion after N
INCONCLUSIVE attempts. Rejected because it violates D-24's honest labeling
principle: underpowered ≠ failed.

**Rationale**: `design_brief.md:133-136` (auto-trigger), `PLAN.md:470-474`
(governance). Round 6 explicit re-trigger: `claude_code/round-6_author-reply.md:77-108`.
Codex confirmation: `codex/round-6_reviewer-reply.md:57-79`.

### Decision 3: Verdict Taxonomy (3 certification verdicts)

**Accepted position**: Three certification-tier verdicts:

| Verdict | Meaning | Next action |
|---------|---------|-------------|
| `CLEAN_OOS_CONFIRMED` | Winner validated by independent evidence | Certification complete |
| `CLEAN_OOS_INCONCLUSIVE` | Reserve underpowered; honest label | Maintain `INTERNAL_ROBUST_CANDIDATE`, wait for more data, re-trigger |
| `CLEAN_OOS_FAIL` | Winner rejected by independent evidence | Phase 3: new research on expanded data |

**Reserve Rollover Invariant**: Attempt N+1 starts strictly after attempt N's
`reserve_end_*`. Prevents re-use of already-evaluated data.

**Rejected alternative**: Binary CONFIRMED/FAIL without INCONCLUSIVE. Rejected
because btc-spot-dev's own WFO experience proves underpowered evaluation is the
common case, not the edge case (`findings-under-review.md:112-114`).

**Rationale**: `findings-under-review.md:87-129` (F-21), `design_brief.md:120-124`
(3-branch flow), `codex/round-3_reviewer-reply.md:144-151` (method-first acceptance).

### Decision 4: Power Rules — Method-First (D-24)

**Accepted position**: Power rules are campaign-specific, predeclared before
reserve opening. No universal gate set frozen in V1.

**Mandatory criteria** (minimum):
- Calendar-time: reserve must span sufficient duration
- Trade count: minimum trades for statistical validity

**Additional dimensions**: method-dependent (regime coverage, exposure hours,
effect size). Determined by pre-registered power method per campaign.

**INCONCLUSIVE auto-path**: If predeclared power method says reserve is
underpowered, verdict is automatically INCONCLUSIVE — no further metric
analysis needed.

**Rejected alternative**: Universal binding dimension set with exact numeric
thresholds. Rejected because trade frequency, strategy structure, and data
arrival rate vary across campaigns — fixed thresholds create false precision.

**Rationale**: `codex/round-3_reviewer-reply.md:144-157` (method-first convergence),
`findings-under-review.md:177-236` (F-24 power dimensions).

### Decision 5: Pre-existing Candidates (D-23 — Judgment call)

**Accepted position** (Claude Code, selected by human researcher):

**Scenario 1 — Same-family rediscovery**: Deferred to Topic 008 / F-13.
Topic 010 does not own family-identity lookup fields or same-family equivalence
semantics. If Topic 008 later exports a same-family relation, Topic 010 may
consume it only for below-certification convergence signaling; Clean OOS is
still required and there is no automatic certification uplift.

**Scenario 2 — Contradiction**: Settled by Topic 007 semantic rule. If
same-archive search contradicts the historical lineage, the artifact MUST
surface that contradiction explicitly and keep it below certification tier
(`debate/007-philosophy-mission/final-resolution.md:90-92`).

**Scenario 3 — NO_ROBUST_IMPROVEMENT with pre-existing candidate**: Frozen
derived invariant. If shadow provenance contains a pre-existing candidate and
the x38 campaign verdict is `NO_ROBUST_IMPROVEMENT`, then that pre-existing
candidate remains unchanged / unadjudicated by x38, below certification tier.
This is not certification, not contradiction, and does not create a new x38
winner.

**Rejected alternative** (Codex): Topic 010 should freeze an explicit
below-certification relation / lookup contract for Scenario 1 and Scenario 3
before closure. Rejected because Scenario 1 depends on Topic 008's identity
schema (F-13, Open) which Topic 010 cannot unilaterally define.

**Rationale**: `judgment-call-deliberation.md` (human decision + tradeoff),
`claude_code/round-6_author-reply.md:171-259` (per-scenario analysis),
`codex/round-6_reviewer-reply.md:108-155` (narrowed position).
**Decision owner**: Human researcher.

---

## Unresolved tradeoffs (for human review)

- **Scenario 1 comparison contract**: Deferred to Topic 008 F-13 (identity
  schema). When Topic 008 closes, the comparison procedure for same-family
  rediscovery should be revisited. Risk: if Topic 008 defines identity axes
  without consulting Topic 010's consumption needs, the interface may require
  adjustment.

- **Cross-attempt escalation**: V1 provides mandatory human review at every
  INCONCLUSIVE iteration. V2+ may add automated escalation triggers if
  operational experience shows reviewers systematically defer. No V1 mechanism
  prevents a reviewer from indefinitely deferring with valid review dates —
  only social/governance pressure.

- **Minimum duration value**: The ≥6 month provisional floor in PLAN.md is not
  frozen by Topic 010. D-24's method-first principle means actual minimum is
  campaign-specific. The 6-month figure remains a planning heuristic, not a
  binding threshold.

---

## Cross-topic impact

| Topic | Impact | Action needed |
|-------|--------|---------------|
| 003 (protocol engine) | Clean OOS is Phase 2 AFTER 8-stage research pipeline, not "Stage 9". 003 must treat Clean OOS as a separate post-pipeline mechanism consuming the frozen winner. | 003 consumes Topic 010's Phase 2 protocol when designing pipeline integration. |
| 008 (architecture & identity) | Scenario 1 comparison contract deferred to F-13 (three-identity-axis model). Topic 010 needs `program_lineage_id` or equivalent for same-family comparison. | 008 should consider Topic 010's consumption need when resolving F-13. |
| 016 (bounded recalibration) | Topic 010's verdicts assume a frozen winner and clean reserve opened once. If 016 allows recalibration, it must define whether recalibrated candidates need new reserve, lightweight re-certification, or no re-certification. | 016 owns the recalibration/certification interaction. Topic 010 is now a satisfied dependency for 016. |
| 017 (epistemic search policy) | ESP-03 consumes Topic 010's power-floor methodology. Promotion ladder should reuse method-first power contract (D-24), not invent parallel fixed thresholds. | 017 consumes D-24's method-first contract. Topic 010 is now a satisfied dependency for 017. |

---

## Draft impact

| Draft | Sections affected | Action needed |
|-------|------------------|---------------|
| `architecture_spec.md` | §6 (Clean OOS Flow) — currently stub | **Create**: Phase 2 lifecycle, verdict taxonomy, auto-trigger, Reserve Rollover Invariant, CertificationVerdict schema, pre-existing candidate treatment, power rules |
| `architecture_spec.md` | §5.2 (3-Tier Claim Model) | **Verify**: certification tier verdicts consistent with D-21 three-verdict taxonomy |
| `architecture_spec.md` | Traceability table | **Add**: D-12, D-21, D-23, D-24 entries |
