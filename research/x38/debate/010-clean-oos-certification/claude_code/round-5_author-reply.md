# Round 5 — Author Reply: Clean OOS & Certification
**Topic**: 010 — Clean OOS & Certification
**Author**: claude_code
**Date**: 2026-03-25
**Responds to**: `codex/round-4_reviewer-reply.md`
**Scope**: X38-D-12, X38-D-21, X38-D-23, X38-D-24
**Artifacts read**:
- `AGENTS.md`
- `docs/online_vs_offline.md`
- `x38_RULES.md` (via AGENTS.md §2 context)
- `debate/rules.md`
- `debate/prompt_template.md`
- `debate/010-clean-oos-certification/README.md`
- `debate/010-clean-oos-certification/findings-under-review.md`
- `debate/010-clean-oos-certification/claude_code/round-1_opening-critique.md`
- `debate/010-clean-oos-certification/codex/round-1_rebuttal.md`
- `debate/010-clean-oos-certification/claude_code/round-2_author-reply.md`
- `debate/010-clean-oos-certification/codex/round-2_reviewer-reply.md`
- `debate/010-clean-oos-certification/claude_code/round-3_author-reply.md`
- `debate/010-clean-oos-certification/codex/round-3_reviewer-reply.md`
- `debate/010-clean-oos-certification/claude_code/round-4_author-reply.md`
- `debate/010-clean-oos-certification/codex/round-4_reviewer-reply.md`
- `docs/design_brief.md:87-148`
- `PLAN.md:460-559`
- `drafts/architecture_spec.md:130-189`
- `debate/007-philosophy-mission/final-resolution.md:85-109`

**MANDATORY RULE REMINDER:**
1. §4: Attack the argument, not the conclusion.
2. §7: Steel-man is required before marking `Converged`.
3. §8: No soft concession language; every concession must be evidence-backed.
4. §12: No new topic creation after round 1.

---

Codex's Round 4 accepts both major mechanism repairs: consumed-reserve-slice schema
(D-12) and Reserve Rollover Invariant (D-21). The surviving disputes are residual
sub-questions in D-12 and D-21, and the non-contradiction carrier in D-23. D-24
remains Converged. This round steel-mans D-12 and D-21 toward convergence (Part A)
and continues D-23 with a refined argument (Part B).

---

## PART A — STEEL-MAN ATTEMPTS

### X38-D-12: Clean OOS via future data

**Steel-man for Codex's Open position** (D-12 retains unresolved sub-questions
beyond the schema repair):

The consumed-reserve-slice gap is closed, but F-12 explicitly declares four
sub-questions open at lines 74-80: minimum duration, module-vs-pipeline placement,
FAIL recording format, and FAIL meta-knowledge treatment. These appear in the
finding itself, not in the debate. D-12 cannot converge if the finding's own
declared open set remains unaddressed — closing on the schema repair alone would
leave acknowledged gaps unresolved.

**Why the steel-man does not hold**:

1. **Minimum duration is resolved by D-24.** F-12:74 labels the 6-month floor as
   "temporary" (`findings-under-review.md:74`); `PLAN.md:467-468` uses the same
   provisional qualifier: "giá trị chính xác còn mở, xem F-12 câu hỏi mở." The
   open question is: "6 tháng đủ? 1 năm? Phụ thuộc trade frequency?"
   (`findings-under-review.md:76`). D-24's converged method-first law answers this
   directly: minimum duration is campaign-specific, determined by the pre-declared
   power method, with mandatory calendar-time criteria
   (`codex/round-3_reviewer-reply.md:144-151`). The answer to "depends on trade
   frequency?" is yes — that is precisely why D-24 converges on method-first rather
   than universal constants. This is not a D-12 gap; it is a D-24 question already
   resolved by D-24's convergence.

2. **Module vs pipeline placement is owned by Topic 003.** Both
   `findings-under-review.md:244` and `README.md:42` explicitly assign this: "003
   owns pipeline structure; 010 defines Clean OOS protocol within that structure."
   The question "Clean OOS nên là module riêng hay tích hợp vào pipeline?"
   (`findings-under-review.md:78`) is a pipeline-architecture question outside
   D-12's scope. D-12 cannot close what Topic 003 owns.

3. **FAIL recording is resolved by the CertificationVerdict schema.** Codex's
   Round 4 explicitly accepts the schema: "those fields are enough to reconstruct
   which clean bars were burned without querying external pipeline state"
   (`codex/round-4_reviewer-reply.md:51-55`). The full lineage is recorded:
   `frozen_spec_ref`, `reserve_boundary_*`, `reserve_end_*`, `append_data_ref`,
   `verdict`, `metrics`, `iteration_count`, `previous_verdicts`
   (`claude_code/round-4_author-reply.md:98-111`).

4. **FAIL meta-knowledge treatment is settled in F-12's own text.** "Winner cũ
   FAIL trở thành historical evidence/provenance (KHÔNG nâng thành anti-pattern —
   PROMPT_FOR_V7_HANDOFF.md line 59 cấm import prior decision outcomes làm
   narrowing priors)" (`findings-under-review.md:39-40`; `PLAN.md:553-555`).
   Round 3 established: FAIL does not enter MetaLesson pipeline, does not create
   an anti-pattern, is recorded immutably in the CertificationVerdict
   (`claude_code/round-3_author-reply.md:239-251`). Codex accepted the
   certification-tier placement (`codex/round-3_reviewer-reply.md:44-49`).

**Conclusion**: Every sub-question in F-12:74-80 is resolved by either (a) D-24's
converged method-first law (minimum duration), (b) Topic 003's declared ownership
(pipeline placement), (c) the accepted CertificationVerdict schema (FAIL
recording), or (d) F-12's own settled text (FAIL meta-knowledge). No sub-question
remains that is both within D-12's scope and unresolved.

**Converged V1 contract for D-12**:
- Clean OOS = Phase 2 after research; reserve = genuinely new data only
- One-shot reserve law with executable timestamp boundaries
- CertificationVerdict schema: `frozen_spec_ref`, `reserve_boundary_*`,
  `reserve_end_*`, `append_data_ref`, `verdict`, `metrics`, `iteration_count`,
  `previous_verdicts`
- FAIL lineage: immutable record in CertificationVerdict; historical
  evidence/provenance, not anti-pattern; no MetaLesson pipeline interaction
- Minimum duration: campaign-specific per D-24 method-first law
- Module placement: deferred to Topic 003
- Auto-trigger: `PENDING_CLEAN_OOS` with no-silent-deferral governance

**Proposed status**: Converged — waiting for Codex to confirm (§7c).

---

### X38-D-21: CLEAN_OOS_INCONCLUSIVE

**Steel-man for Codex's Open position** (repeated-INCONCLUSIVE needs an
upper-bound / escalation rule):

The rollover invariant ensures evaluation validity, but governance validity is
separate. Without an explicit upper bound on INCONCLUSIVE attempts, a reviewer
could defer indefinitely through an arbitrarily long sequence of individually
compliant "wait and re-run" cycles. The `iteration_count` + `previous_verdicts`
fields make the accumulation pattern visible but do not guarantee a resolution
response. "Can see the pattern" is weaker than "must act on the pattern."

**Why the steel-man does not hold**:

1. **Automatic count-based FAIL conversion violates D-24's honest labeling.**
   D-24's converged principle: "honest INCONCLUSIVE when [the method says] the
   reserve is underpowered" (`codex/round-3_reviewer-reply.md:137-138,149-151`;
   `PROMPT_FOR_V[n]_CLEAN_OOS_V2[en].md:76-82` [extra-archive]). Converting
   INCONCLUSIVE to FAIL after N attempts would produce a FAIL verdict without the
   evidence required for FAIL. The reserve was underpowered, not negative. A forced
   FAIL is a false verdict: the framework would claim "winner failed certification"
   when the honest assessment is "certification still lacks statistical power." This
   directly contradicts D-24's frozen honest-labeling principle.

2. **Human judgment IS the escalation mechanism at every iteration.**
   `PENDING_CLEAN_OOS` fires at each INCONCLUSIVE with mandatory review
   (`PLAN.md:470-474`): the human must act or explicitly defer with a review date.
   The enriched artifact provides full context: `iteration_count` shows attempt
   number, `previous_verdicts` shows the accumulated pattern. The question "after
   how many attempts does the framework force human judgment?" has the answer: at
   every single one. The framework does not wait for N attempts before engaging
   human judgment — it requires human judgment on each INCONCLUSIVE. This is
   stronger governance than a count-based trigger: the human sees and must respond
   to the full accumulation at every iteration, not just after a threshold.

3. **Data arrival rate bounds re-run frequency.** Each re-run requires genuinely
   new data via the Reserve Rollover Invariant
   (`claude_code/round-4_author-reply.md:172-193`, accepted by Codex). Data arrives
   at a bounded rate (the market produces bars in real time). Unbounded re-runs per
   unit calendar time are physically impossible — the invariant and data physics
   together constrain the sequence.

4. **Count-based escalation is a V2+ governance refinement, not a V1 gap.** V1
   provides: mandatory human review with full accumulated context at each iteration,
   no silent deferral, honest labeling. If operational experience shows that
   reviewers systematically fail to act on visible accumulation patterns, V2+ adds
   automated escalation triggers. But V1 is not incomplete: it places the
   resolution authority where it belongs — human researcher (per
   `debate/rules.md:78`, §15) — with the information needed to exercise judgment.
   The same D-24 principle applies: V1 freezes the method-first framework, not
   universal constants that bind all future campaigns.

**Conclusion**: The upper-bound question has an answer that is already in the
design: human judgment at every INCONCLUSIVE iteration, mandatory and
accumulation-aware. Automatic FAIL conversion violates honest labeling. A
count-based escalation threshold would need to be universal (V1) or
campaign-specific (already handled by human judgment per iteration). No mechanism
gap remains.

**Converged V1 contract for D-21**:
- Three certification verdicts: CONFIRMED, INCONCLUSIVE, FAIL (no fourth state)
- Reserve Rollover Invariant: attempt N+1 starts strictly after attempt N's
  `reserve_end_*`
- Enriched artifact: `iteration_count` + `previous_verdicts` (mandatory fields)
- Governance: `PENDING_CLEAN_OOS` fires at each INCONCLUSIVE with mandatory
  human review, explicit deferral + review date, no silent postponement
- Human researcher = escalation authority at every iteration
- No automatic count-based FAIL conversion (violates D-24 honest labeling)

**Proposed status**: Converged — waiting for Codex to confirm (§7c).

---

### X38-D-24: Clean OOS power rules

No dispute remains. Converged since Round 3, confirmed in Round 4 by both sides
(`codex/round-4_reviewer-reply.md:120-129`). Acknowledged.

---

## PART B — CONTINUED DEBATE

### X38-D-23: Pre-existing candidates vs x38 winners

Codex's Round 4 narrows the dispute to a precise point: "the non-contradiction
relation to historical lineage still has no defined carrier"
(`codex/round-4_reviewer-reply.md:115-116`). Codex explicitly disclaims
MUST-surface symmetry: "This is not a demand for contradiction-style MUST-surface
symmetry across all cases" (line 114). The claim is about artifact-level coverage.

I maintain that Scenarios 1 and 3 ARE covered at the artifact level. Codex's
Round 4 counter-arguments are addressed below.

**On Scenario 1 — same-family rediscovery**:

Codex: "no current artifact is required to state that the x38 result and the
historical candidate are the same family" (lines 94-97).

The campaign's same-archive evidence output records what the campaign found —
including the winner's structural identity (which algorithm family, which
parameter family). The shadow-only provenance records the pre-existing candidate's
structural identity. The relation between x38's output and historical lineage is a
deterministic comparison of two recorded values: x38 winner family identity (in
campaign evidence) vs historical candidate family identity (in shadow-only
provenance). This is not "manually inferable" in the sense of requiring subjective
judgment — it is a factual comparison of two machine-readable artifact fields.

Codex distinguishes "manually inferable" from "recorded relation." But the
relation IS recorded — distributed across two artifacts that are both mandatory
outputs of the framework. The campaign evidence records one side (what x38 found);
shadow-only provenance records the other (what existed before). A "defined carrier"
for the relation already exists: it is the pair (campaign evidence, shadow-only
provenance), each recording its respective domain.

Requiring a SINGLE artifact to state the combined relation introduces a problem the
sources do not address: what constitutes "same family"? If x38 discovers a
D1-family trend-follower with different parameters, trail logic, or filter
structure than E5_ema21D1, is that "same family"? The semantic rule handles this
for contradiction by surfacing it for human judgment
(`debate/007-philosophy-mission/final-resolution.md:90-92`). For non-contradiction,
no source specifies a family-equivalence criterion. The single-artifact carrier
Codex requests would need to include a family-comparison standard that does not
exist in the design.

**On Scenario 3 — NO_ROBUST_IMPROVEMENT**:

Codex: "NO_ROBUST_IMPROVEMENT ... does not record that a pre-existing candidate
existed and remained neither confirmed nor contradicted" (lines 105-108).

`NO_ROBUST_IMPROVEMENT` records the campaign's complete and honest finding: no
robust winner was produced. Whether a pre-existing candidate exists is not a
campaign-level fact — it is a historical-lineage fact recorded in shadow-only
provenance per MK-17 (`docs/design_brief.md:87-89`). The campaign operates without
knowledge of external candidates by design: MK-17 makes empirical priors
shadow-only on the same dataset. Requiring the campaign verdict to reference
external candidates would import historical-lineage awareness into a
campaign-level artifact, crossing the separation that MK-17 deliberately
establishes.

The pre-existing candidate's status is unchanged by definition: the campaign
produced no output that could change it (no winner, no contradiction, no
confirmation). "Unchanged" is the null state — recording it adds zero information
beyond what is already derivable from (campaign verdict = no winner) + (shadow-only
provenance = candidate exists). Codex states a downstream reader "cannot
distinguish ordinary no-winner output from the specific F-23 case" (lines 109-112).
But the distinction is available: check shadow-only provenance. If a pre-existing
candidate exists in provenance, the reader knows this is the F-23 case. If not, it
is ordinary no-winner. The lookup is one artifact read, not subjective inference.

**On "defined carrier" without MUST-surface**:

Codex disclaims MUST-surface symmetry but still demands a "defined carrier." This
creates a gap in the argument: a carrier serves an obligation, and without
specifying the obligation level, the carrier requirement is procedurally
incomplete. If the obligation is MUST-surface, Topic 007 already decided that only
contradiction qualifies (`debate/007-philosophy-mission/final-resolution.md:90-92`).
If the obligation is something weaker (SHOULD-record, MAY-annotate), no source
establishes such an obligation for non-contradiction. A "defined carrier" without a
defined obligation is a mechanism searching for a requirement.

The V1 design principle throughout this topic has been: freeze obligations that
sources back, defer specifics to per-campaign methods (D-24), avoid adding
mechanisms that lack source authority. Applying this principle to D-23: sources back
MUST-surface for contradiction (covered by Scenario 2). Sources do not back any
obligation level for non-contradiction. Adding a recording contract for
non-contradiction would be the first V1 obligation in this topic without source
authority.

**Proposed status**: Open — pending Codex's evaluation. If Codex can specify
(a) the obligation level the carrier would serve (MUST/SHOULD/MAY) with source
authority for that level, or (b) a specific downstream decision that requires a
single-artifact carrier rather than the two-artifact lookup (campaign evidence +
shadow-only provenance), I will address it. If neither can be established, D-23
should converge on: Scenario 2 covered by Topic 007 semantic rule; Scenarios 1 and
3 covered by existing two-artifact design (campaign evidence + shadow-only
provenance), no additional recording obligation.

---

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-D-12 | F-12:74-80 sub-questions all resolved: minimum duration → D-24 method-first; pipeline placement → Topic 003; FAIL recording → CertificationVerdict (Codex R4 accepted); FAIL meta-knowledge → F-12 text (provenance, not anti-pattern) | Judgment call | Open | D-12 retains unresolved sub-questions beyond the consumed-reserve-slice schema repair, per F-12:74-80 | Each sub-question resolved by either D-24 convergence, Topic 003 ownership, accepted CertificationVerdict schema, or F-12's own settled text; no sub-question remains both in-scope and unresolved |
| X38-D-21 | Upper bound = human judgment at every INCONCLUSIVE iteration (PENDING + enriched artifact + no-silent-deferral); automatic FAIL conversion violates D-24 honest labeling; data arrival rate bounds frequency | Thiếu sót | Open | Rollover invariant accepted, but repeated-INCONCLUSIVE still lacks an upper-bound/escalation rule beyond reviewer visibility | Count-based FAIL = false verdict (underpowered ≠ failed); human judgment fires at every iteration, not after N; data physics bounds re-run frequency; V2+ refinement, not V1 gap |
| X38-D-23 | Two-artifact design (campaign evidence + shadow-only provenance) covers non-contradiction relation; single-carrier merger crosses MK-17 separation; "defined carrier" without defined obligation is procedurally incomplete; no source backs non-contradiction recording obligation | Thiếu sót | Open | Round 4 schema repairs and subtype concession accepted; non-contradiction relation to historical lineage still has no defined single-artifact carrier | Two-artifact carrier is legitimate: each artifact records its domain; comparison is deterministic on recorded values; family-equivalence criterion undefined in sources; carrier without obligation = mechanism without requirement; V1 principle: freeze source-backed obligations only |
| X38-D-24 | Method-first power law frozen: pre-declared method, honest INCONCLUSIVE, calendar/trade-count mandatory, extra dimensions method-dependent | Thiếu sót | Converged | — (confirmed by both sides, Rounds 3-4) | — |
