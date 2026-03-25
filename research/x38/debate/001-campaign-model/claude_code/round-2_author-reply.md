# Round 2 — Author Reply: Campaign Model

**Topic**: 001 — Campaign Model
**Author**: claude_code
**Date**: 2026-03-23
**Responds to**: `codex/round-1_rebuttal.md`
**Scope**: All findings — X38-D-03, X38-D-15, X38-D-16
**Artifacts read**:
- `debate/rules.md`
- `debate/prompt_template.md`
- `debate/001-campaign-model/findings-under-review.md`
- `debate/001-campaign-model/README.md`
- `debate/001-campaign-model/claude_code/round-1_opening-critique.md`
- `debate/001-campaign-model/codex/round-1_rebuttal.md`
- `debate/007-philosophy-mission/final-resolution.md`
- `debate/004-meta-knowledge/final-resolution.md`
- `debate/000-framework-proposal/findings-under-review.md`
- `docs/design_brief.md`
- `docs/online_vs_offline.md`
- `PLAN.md`
- `EXECUTION_PLAN.md`

**MANDATORY RULE REMINDER:**
1. §4: Attack the argument, not the conclusion.
2. §7: Steel-man is required before marking `Converged`.
3. §8: No soft concession language; every concession must be evidence-backed.
4. §12: No new topic creation after round 1.

---

Codex's rebuttal narrows all three disputes. The high-level diagnoses (grouping is
needed, metric scoping is needed, transition gap is real) were never contested. The
arguments concern mechanism specificity, scope ownership, and numeric overreach.
After evidence review, I move all three issues toward convergence with
evidence-backed concessions.

§7 note: per §7(a), "steel-man" below refers to the strongest remaining argument
for my old position — the position I am moving away from.

---

## PART A — STEEL-MAN ATTEMPTS

### X38-D-03: Campaign → Session model

**Steel-man for my old position** (a first-class Campaign lifecycle object is
required, not just metadata grouping):

A lifecycle object (PLANNED → ACTIVE → DONE) enforces the methodology boundary by
construction: once a campaign transitions to DONE, no session can be added to it.
Passive metadata (`campaign_id` + `protocol_hash`) is mutable — a session record
can be re-tagged or a hash field modified after creation, silently breaking the
invariant that sessions within a campaign share identical protocol. Only a
first-class object with immutable state transitions prevents this class of error
without requiring a separate validation step.

**Why the steel-man does not hold**:

1. **Enforcement is achievable without a lifecycle object.** A session record with
   `{campaign_id, dataset_sha256, protocol_sha256}` as immutable-after-creation
   fields, plus a constraint that all sessions sharing `campaign_id` must have
   identical hashes, provides the same invariant. This is a standard database
   constraint pattern — equally effective, fewer concepts. Codex's alternative
   (`round-1_rebuttal.md:50`: "dataset hash + protocol hash + explicit HANDOFF
   records") satisfies the invariant.

2. **MK-17 shadow-only weakens the same-data campaign boundary.** `PLAN.md:491-494`
   explicitly states: "C2 ≈ thêm batch sessions cho C1" on the same dataset. The
   design authority itself considers same-data C2 functionally equivalent to
   extending C1. The heavyweight boundary between same-data campaigns provides
   overhead without proportional enforcement value. The meaningful transition is
   the methodology change — captured by `protocol_sha256` changing, regardless of
   container shape.

3. **K=2 and N≥3 are ownership violations.** `PLAN.md:950-957` assigns convergence
   methodology to Topic 013: "Topic 001 định nghĩa cấu trúc (what is a campaign),
   topic 013 định nghĩa thuật toán (how to measure convergence)." Embedding exact
   numeric floors in the campaign model conflates structure with algorithm. Topic
   001 can require "sufficient sessions for convergence analysis" — the exact floor
   is a convergence-algorithm output, not a campaign-model input.

**Conclusion**: The evidence converges on **required properties**, not container
shape. Any implementation satisfying all four properties below is acceptable:

1. **Methodology boundary** — sessions within a group share identical protocol
   (immutable after group creation).
2. **HANDOFF law** — transition between groups requires formal justification.
3. **Convergence scope** — the group defines the unit of convergence analysis.
4. **Lineage tracking** — groups form an explicit chain with provenance.

Whether these are implemented as a first-class lifecycle object or as
metadata-with-constraints is an architecture-spec decision.

**Proposed status**: Converged — waiting for Codex to confirm (§7c).

---

### X38-D-15: Metric scoping — two scopes → three scopes

**Steel-man for my old position** (two offline-native scopes suffice; third scope
deferred to Topic 016):

Topic 007 Decision 2 (`final-resolution.md:56-62`) defines two verdict-bearing
tiers: Campaign and Certification. The cleanest semantic mapping is 1:1 — each
verdict tier corresponds to exactly one metric scope. Adding a third scope within
Topic 001 creates a dependency on methodology that Topic 016 owns (bounded
recalibration), risking scope creep before upstream decisions are settled. The
third scope can wait until 016 defines what cross-campaign comparison looks like.

**Why the steel-man does not hold**:

1. **Verdict tiers are not metric tiers.** Codex correctly identifies
   (`round-1_rebuttal.md:64`): Topic 007 froze claim semantics (what verdicts mean),
   not measurement boundaries (what gets measured where). Campaign verdicts
   aggregate session results, but HANDOFF decisions between campaigns require
   comparing ACROSS campaigns. This comparison falls outside both session-scoped
   and campaign-scoped metrics. The mapping I assumed (2 verdict tiers → 2 metric
   scopes) confuses claim authority with measurement boundary — two orthogonal
   concepts.

2. **My Round 1 attack was wrong-target.** `findings-under-review.md:105-125`
   already translates F-15 into x38-native terms: session-scoped, campaign-scoped,
   and cross-campaign metrics. My opening critique (`opening-critique.md:123-146`)
   attacked the gen4 vocabulary (`freeze_cutoff_utc`, `cumulative_anchor_utc`)
   rather than the x38-native claim. Rejecting provenance vocabulary does not
   defeat the live argument. This is a §4 violation on my part: I attacked the
   framing source instead of the argument.

3. **Deferring to Topic 016 is an ownership error.** `EXECUTION_PLAN.md:209` makes
   Topic 016 downstream of Topic 001: "Phụ thuộc: 001 + 002 + 010 + 011 + 015
   (tất cả phải CLOSED)." If 001 refuses to define the third scope, 001 loses the
   ability to specify what evidence justifies "open C2" versus "add sessions to
   C1" — a question I myself raised (`opening-critique.md:87-101`). Answering
   that question requires cross-campaign comparison, which requires the third
   scope to exist.

**Conclusion**: Three metric scopes are needed:

1. **Session-scoped** — candidate ranking within one deterministic session.
2. **Campaign-scoped** — convergence analysis across sessions within one campaign.
3. **Cross-campaign/HANDOFF-scoped** — lineage accounting and transition
   justification.

V1 content of the third scope is minimal per MK-17 shadow-only
(`debate/004-meta-knowledge/final-resolution.md:193`): lineage and HANDOFF
accounting only, no active empirical ranking channel. Codex agrees with this
narrowing (`round-1_rebuttal.md:68`): "the third scope may be minimal
lineage/HANDOFF accounting in v1, not an active empirical ranking channel."

Ownership split:
- Topic 001: defines existence, purpose, and boundary of all three scopes.
- Topic 013: owns convergence methodology within campaign-scoped metrics.
- Topic 016: owns bounded recalibration decisions using cross-campaign scope.

**Proposed status**: Converged — waiting for Codex to confirm (§7c).

---

### X38-D-16: Campaign transition guardrails

**Steel-man for my old position** (full HANDOFF Protocol with specific controls —
exact one-change rule, budget numbers, four triggers including
`data_integrity_fail`):

Without concrete numbers and a defined budget, "bounded change" becomes a
rubber-stamp process. A researcher can always write a dossier claiming "one
principal change" while actually modifying multiple interacting methodology
dimensions. Gen4's explicit budget (`{max_methodology_rules: 1,
max_search_heuristics: 3, max_pipeline_stages: 1}`) provides a falsifiable
constraint: either the HANDOFF fits the budget or it doesn't. Additionally, the
four-trigger enum (`convergence_stall`, `methodology_gap`, `pipeline_bug`,
`data_integrity_fail`) covers the complete failure-mode space — removing any
trigger leaves gaps.

**Why the steel-man does not hold**:

1. **Gen4's budget numbers lack offline calibration basis.** Gen4's specific
   numbers are tied to 180-day forward-evidence economics
   (`x37/docs/gen4/core/research_constitution_v4.0.yaml:95-176` [extra-archive]),
   which same-data offline campaigns do not share
   (`round-1_rebuttal.md:82`). Transplanting exact numbers without the
   underlying calibration evidence is arbitrary. The PRINCIPLE (bounded change
   scope) survives; the exact magnitudes have no x38 evidence basis to freeze now.

2. **`data_integrity_fail` is not a HANDOFF trigger.** The dataset snapshot is
   SHA-256-verified at campaign creation (`PLAN.md:445-446`; `docs/design_brief.md:
   96-97`). Post-creation integrity failure is an invalid-run / abort scenario —
   it requires re-running on the verified snapshot, not transitioning to a new
   campaign with new methodology. Codex's four-case taxonomy
   (`round-1_rebuttal.md:87-91`) correctly separates this from evidence-bearing
   HANDOFF.

3. **The do-not-touch list creates parallel policy authority.** Topic 002 owns the
   content gate — what may or may not flow across campaign boundaries
   (`debate/004-meta-knowledge/final-resolution.md:190`: "Content gate /
   F-06 single ownership (topic 002)"). My HANDOFF dossier's do-not-touch list
   duplicates this authority. The dossier should REFERENCE firewall constraints
   (→ Topic 002), not establish a parallel policy source.

4. **N≥3 and pairwise agreement thresholds belong to Topic 013.** `PLAN.md:956-957`:
   "topic 013 định nghĩa thuật toán (how to measure convergence)." Embedding
   exact numeric thresholds in the HANDOFF law embeds convergence-algorithm
   outputs in campaign structure.

**Conclusion**: The gap is real (C-06 confirms: `debate/000-framework-proposal/
findings-under-review.md:30`). The HANDOFF law should freeze vocabulary and
principles; exact thresholds belong downstream.

**Refined failure-mode taxonomy** (incorporating Codex's four-case separation):

| Mode | Semantics | Mechanism | Owner |
|------|-----------|-----------|-------|
| Invalid run | Data integrity failure, runtime error | Abort + re-run within current campaign | 001 |
| Corrective rerun | Pipeline bug affecting reproducibility | New session within current campaign, bug fix applied | 001 |
| Genuine HANDOFF | Convergence stall or identified methodology gap | New campaign with dossier | 001 (law) + 013 (thresholds) |
| New-data restart | Certification FAIL on new data | Phase 2 → Phase 3 transition (`design_brief.md:126-129`) | 010 |

**HANDOFF Protocol** (what Topic 001 freezes):

```
HANDOFF = {
    trigger:        one of {convergence_stall, methodology_gap},
    principle:      single principal hypothesis
                    (change one methodology dimension per transition),
    dossier:        {convergence_summary, gap_evidence, proposed_change,
                     firewall_ref (→ Topic 002 content gate)},
    bounded_scope:  change budget required — exact numbers NOT frozen by 001
}
```

What Topic 001 defers:
- Exact convergence stall definition → Topic 013
- Exact change budget numbers → architecture spec or Topic 013
- Content filtering at HANDOFF boundary → Topic 002
- Bounded recalibration across campaigns → Topic 016

**Proposed status**: Converged — waiting for Codex to confirm (§7c).

---

## PART B — CONTINUED DEBATE

No issues remain in continued debate. All three issues are proposed for convergence
in Part A.

---

## Cross-topic tensions (updated)

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 007 (philosophy) | X38-D-01 | F-01 constrains campaign stop conditions: `NO_ROBUST_IMPROVEMENT` must be valid exit | 007 CLOSED; constraint inherited, 001 owns operationalization |
| 002 (firewall) | X38-D-04 | Firewall determines what can flow at HANDOFF — HANDOFF dossier references firewall, does not duplicate it | 002 owns content gate; 001 owns HANDOFF trigger/dossier/principle |
| 010 (clean-oos) | X38-D-12, X38-D-21 | Clean OOS depends on campaign model defining Phase 1 exit criteria; new-data restart is Phase transition (010), not HANDOFF (001) | 010 owns certification; 001 defines campaign-level verdicts |
| 013 (convergence) | F-15 scoping | Metric scoping defines convergence analysis boundaries; convergence stall thresholds and session minimums are convergence-algorithm outputs | 013 owns convergence methodology + exact thresholds; 001 provides scope definitions + HANDOFF vocabulary |
| 016 (bounded-recalibration) | C-04, C-12 | Cross-campaign scope defined by 001; recalibration decisions using that scope owned by 016 | 016 owns decision; 001 provides HANDOFF mechanism + third scope definition |

---

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-D-03 | Required PROPERTIES over container shape: methodology boundary, HANDOFF law, convergence scope, lineage. K=2 and N≥3 → Topic 013. Implementation shape → architecture spec | Judgment call | Proposed Converged (§7c pending) | Lifecycle object enforces methodology boundary by construction; metadata fields can be mutated, breaking session-protocol invariant | Immutable hash constraints provide equal enforcement; MK-17 makes same-data boundary lightweight (`PLAN.md:491-494`); numeric floors are convergence outputs (`PLAN.md:950-957`) |
| X38-D-15 | Three metric scopes: session, campaign, cross-campaign/HANDOFF. Third scope v1 = lineage/HANDOFF accounting only (MK-17 shadow-only). Ownership: 001 defines scopes, 013 owns convergence methodology, 016 owns recalibration | Thiếu sót | Proposed Converged (§7c pending) | Two scopes map 1:1 to Topic 007's two verdict tiers; third scope deferred to 016 avoids premature dependency | Verdict tiers ≠ metric tiers (different semantic axis); wrong-target attack on gen4 vocabulary (§4); deferral to 016 is ownership error (`EXECUTION_PLAN.md:209`: 016 downstream of 001) |
| X38-D-16 | HANDOFF law with trigger vocabulary {convergence_stall, methodology_gap}, single-hypothesis principle, dossier with firewall reference. Four failure modes separated (invalid run / corrective rerun / genuine HANDOFF / new-data restart). Exact budget numbers NOT frozen | Thiếu sót | Proposed Converged (§7c pending) | Specific budget numbers needed for falsifiable constraint; four triggers cover complete failure-mode space | Gen4 numbers lack offline calibration basis; data_integrity_fail is invalid-run not HANDOFF; do-not-touch overlaps Topic 002 ownership; numeric thresholds → Topic 013 |
