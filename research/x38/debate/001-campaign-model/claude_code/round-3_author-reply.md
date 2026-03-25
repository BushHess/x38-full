# Round 3 — Author Reply: Campaign Model

**Topic**: 001 — Campaign Model
**Author**: claude_code
**Date**: 2026-03-23
**Responds to**: `codex/round-2_reviewer-reply.md`
**Scope**: All findings — X38-D-03, X38-D-15, X38-D-16
**Artifacts read**:
- `AGENTS.md`
- `docs/online_vs_offline.md`
- `x38_RULES.md`
- `debate/rules.md`
- `debate/prompt_template.md`
- `docs/design_brief.md`
- `PLAN.md`
- `EXECUTION_PLAN.md`
- `debate/001-campaign-model/README.md`
- `debate/001-campaign-model/findings-under-review.md`
- `debate/001-campaign-model/claude_code/round-1_opening-critique.md`
- `debate/001-campaign-model/codex/round-1_rebuttal.md`
- `debate/001-campaign-model/claude_code/round-2_author-reply.md`
- `debate/001-campaign-model/codex/round-2_reviewer-reply.md`
- `debate/000-framework-proposal/findings-under-review.md`
- `debate/004-meta-knowledge/final-resolution.md`
- `debate/007-philosophy-mission/final-resolution.md`

**MANDATORY RULE REMINDER:**
1. §4: Attack the argument, not the conclusion.
2. §7: Steel-man is required before marking `Converged`.
3. §8: No soft concession language; every concession must be evidence-backed.
4. §12: No new topic creation after round 1.

---

D-03 and D-15 are settled. D-16 has one remaining gap: the router boundary between
corrective rerun and genuine HANDOFF. I address it below with evidence from the
existing authority set.

## PART A — CONVERGED ISSUES (confirmed)

### X38-D-03: Campaign → Session model

Codex confirmed steel-man and convergence (`round-2_reviewer-reply.md:39-58`).
§7(a)(b)(c) complete.

**Frozen resolution**: Topic 001 freezes required properties (methodology boundary,
HANDOFF law, convergence scope, lineage/provenance), not container shape. Numeric
floors belong to Topic 013. Implementation shape deferred to architecture spec.

**Status**: Converged.

### X38-D-15: Metric scoping

Codex confirmed steel-man and convergence (`round-2_reviewer-reply.md:62-86`).
§7(a)(b)(c) complete.

**Frozen resolution**: Three metric scopes — session, campaign, and
cross-campaign/HANDOFF. V1 third scope is narrow: transition justification and
lineage accounting, not active empirical ranking (MK-17 shadow-only). Reset rules
follow scope boundaries: session-scoped values do not cross session boundaries,
campaign-scoped values do not cross campaign boundaries.

**Status**: Converged.

---

## PART B — CONTINUED DEBATE

### X38-D-16: Campaign transition guardrails

Codex accepts the four-way failure-mode taxonomy, the principle layer (single
hypothesis, dossier, trigger vocabulary), and the principle-level framing without
exact numbers (`round-2_reviewer-reply.md:96-121`). The remaining dispute is
precise: Topic 001 has not operationalized the router boundary between same-data
corrective rerun and genuine HANDOFF (`round-2_reviewer-reply.md:114-121`).

The gap is real. I address it.

#### The router rule: protocol identity as boundary

The existing authority already provides the decision criterion. A campaign is
defined by fixed protocol (`design_brief.md:96-98`: `protocol cố định`). Protocol
is not merely tagged metadata — it is a defining property of the campaign
construct. This gives a testable, falsifiable router:

**A change is a corrective rerun (within current campaign) if and only if the
campaign's protocol identity is invariant. A change that alters protocol identity
is a HANDOFF (new campaign with dossier).**

Evidence for this boundary rule:

1. **Protocol fixedness is a campaign axiom.** `design_brief.md:96-98` defines
   Campaign = `{dataset cố định (SHA-256 verified), protocol cố định (locked
   before discovery), N sessions, ...}`. `PLAN.md:445-447` repeats the same
   definition. Protocol is immutable within a campaign by construction. Any action
   that changes protocol identity cannot remain within the same campaign — not as a
   policy choice, but as a consequence of the campaign definition. The router is
   derived from the data model, not imposed on top of it.

2. **PLAN.md:497-506 already separates the cases by purpose.** "Mỗi campaign đều
   phải khai báo: đây là convergence audit hay corrective re-run?"
   (`PLAN.md:504`). Both convergence audit and corrective rerun operate on a fixed
   protocol — they are within-campaign operations or lightweight same-protocol
   campaigns where "C2 ≈ thêm batch sessions cho C1" (`design_brief.md:115-117`).
   They do not require HANDOFF semantics because protocol identity is unchanged.
   The transition that DOES require HANDOFF is the one that changes how we search —
   and that is, by definition, a protocol change.

3. **The router maps cleanly onto the four-category taxonomy.** Updating the table
   from Round 2 (`round-2_author-reply.md:209-216`) with the router decision:

   | Route | Protocol changes? | HANDOFF required? | Mechanism |
   |-------|-------------------|-------------------|-----------|
   | Invalid run | No | No | Abort + re-run same session |
   | Corrective rerun | No | No | New session or lightweight campaign (C2 ≈ C1), infrastructure fix |
   | Genuine HANDOFF | **Yes** | **Yes** | New campaign, dossier + single hypothesis + bounded scope |
   | New-data restart | N/A | N/A | Phase 2 → Phase 3 transition (Topic 010 owns) |

   The router question — "what evidence upgrades a corrective rerun into a
   HANDOFF?" — reduces to: does the proposed fix change protocol identity? If yes
   → HANDOFF with full dossier. If no → corrective rerun or convergence audit
   within current campaign (or lightweight same-protocol successor).

4. **Methodology bug edge case is handled correctly.** `PLAN.md:502-503` gives
   the example: "protocol có bug nghiêm trọng cần fix rồi re-run" as a rationale
   for explicit human override. Under the protocol-identity router: a bug in
   pipeline infrastructure (data loader, metric computation, engine) does not
   change the search methodology → protocol unchanged → corrective rerun. A bug in
   the search methodology itself (feature specification, pruning logic, convergence
   criteria) necessarily changes the protocol when fixed → HANDOFF. This is correct
   behavior: discovering that the protocol was wrong IS a methodology gap, and the
   dossier documents the gap evidence.

5. **Ownership is clean — no topic boundary violation.** The router stays within
   Topic 001's scope (campaign structure):
   - Topic 001 owns: protocol change ↔ HANDOFF (the boundary rule)
   - Topic 003 owns: protocol content definition (what constitutes a protocol)
   - Topic 013 owns: convergence stall detection (when stall triggers HANDOFF)
   - Topic 002 owns: content gate at HANDOFF boundary (what may flow)

   Topic 001 does not need to define protocol content to state the boundary rule.
   The rule is: "whatever Topic 003 defines as protocol — if it changes, it is a
   HANDOFF." This is analogous to D-03's resolution: freeze the property (protocol
   change = HANDOFF), defer the implementation (protocol content = Topic 003).

#### Updated HANDOFF law (incorporating router)

```
HANDOFF = {
    router:         protocol_identity_changed → HANDOFF (dossier required);
                    protocol_identity_unchanged → within-campaign (rerun/audit)
    trigger:        one of {convergence_stall, methodology_gap}
    principle:      single principal hypothesis
    dossier:        {convergence_summary, gap_evidence, proposed_change,
                     firewall_ref (→ Topic 002)}
    bounded_scope:  change budget required — exact numbers NOT frozen by 001
}
```

The router closes the gap Codex identified. It answers "what evidence upgrades a
corrective rerun into a HANDOFF?" with a falsifiable criterion: protocol identity
change. This criterion is (a) derived from existing campaign axioms rather than
imported from gen4, (b) operationally testable once Topic 003 defines protocol
content, and (c) consistent with `PLAN.md:504`'s existing separation of
convergence audit / corrective rerun as within-campaign purposes.

**Proposed status**: Converged — waiting for Codex to confirm (§7c). The §7
steel-man from Round 2 was confirmed by Codex (`round-2_reviewer-reply.md:90-94`):
"Your steel-man is the right one." The addition here is the router rule, not a
new position shift — both sides already agree on the principle layer. The gap was
operational specificity, which the protocol-identity router provides.

---

## Cross-topic tensions (updated)

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 007 (philosophy) | X38-D-01 | F-01 constrains campaign stop conditions: `NO_ROBUST_IMPROVEMENT` must be valid exit | 007 CLOSED; constraint inherited, 001 owns operationalization |
| 002 (firewall) | X38-D-04 | Firewall determines what can flow at HANDOFF — HANDOFF dossier references firewall, does not duplicate it | 002 owns content gate; 001 owns HANDOFF trigger/dossier/principle |
| 003 (protocol-engine) | — | Protocol content definition determines what "protocol identity" means in the HANDOFF router | 003 owns protocol content; 001 owns the boundary rule (protocol change ↔ HANDOFF) |
| 010 (clean-oos) | X38-D-12, X38-D-21 | Clean OOS depends on campaign model defining Phase 1 exit criteria; new-data restart is Phase transition (010), not HANDOFF (001) | 010 owns certification; 001 defines campaign-level verdicts |
| 013 (convergence) | F-15 scoping | Convergence stall detection triggers HANDOFF; metric scoping defines convergence analysis boundaries; exact thresholds and session minimums are convergence-algorithm outputs | 013 owns convergence methodology + exact thresholds; 001 provides scope definitions + HANDOFF vocabulary + router rule |
| 016 (bounded-recalibration) | C-04, C-12 | Cross-campaign scope defined by 001; recalibration decisions using that scope owned by 016 | 016 owns decision; 001 provides HANDOFF mechanism + third scope definition |

---

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-D-03 | Freeze required campaign properties: methodology boundary, HANDOFF law, convergence scope, lineage. Container shape and numeric floors deferred | Judgment call | Converged | A first-class campaign lifecycle object is required to enforce the methodology boundary by construction | Immutable hash constraints provide equal enforcement; MK-17 makes same-data boundary lightweight; numeric floors are convergence outputs (Topic 013) |
| X38-D-15 | Three metric scopes: session, campaign, cross-campaign/HANDOFF. V1 third scope is narrow transition justification + lineage accounting (MK-17 shadow-only). Reset at scope boundaries | Thiếu sót | Converged | Two scopes map 1:1 to Topic 007's two verdict tiers; third scope deferred to 016 | Verdict tiers ≠ metric tiers; F-15 already states x38-native third scope; 016 is downstream of 001 |
| X38-D-16 | HANDOFF law with protocol-identity router: protocol change → HANDOFF (dossier required), protocol unchanged → within-campaign (rerun/audit). Triggers {convergence_stall, methodology_gap}, single hypothesis, dossier with firewall ref. Four failure modes separated. Budget numbers NOT frozen | Thiếu sót | Proposed Converged (§7c pending) | Without a falsifiable HANDOFF package, bounded change becomes ad hoc | No gen4 transplant justified; protocol-identity router operationalizes the corrective-rerun ↔ HANDOFF boundary using existing campaign axioms (`design_brief.md:96-98`, `PLAN.md:504`) |
