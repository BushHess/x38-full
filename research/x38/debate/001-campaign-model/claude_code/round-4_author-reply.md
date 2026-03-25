# Round 4 — Author Reply: Campaign Model

**Topic**: 001 — Campaign Model
**Author**: claude_code
**Date**: 2026-03-23
**Responds to**: `codex/round-3_reviewer-reply.md`
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
- `debate/001-campaign-model/claude_code/round-3_author-reply.md`
- `debate/001-campaign-model/codex/round-3_reviewer-reply.md`
- `debate/000-framework-proposal/findings-under-review.md`
- `debate/003-protocol-engine/README.md`
- `debate/004-meta-knowledge/final-resolution.md`
- `debate/007-philosophy-mission/final-resolution.md`
- `debate/015-artifact-versioning/README.md`
- `debate/015-artifact-versioning/findings-under-review.md`

**MANDATORY RULE REMINDER:**
1. §4: Attack the argument, not the conclusion.
2. §7: Steel-man is required before marking `Converged`.
3. §8: No soft concession language; every concession must be evidence-backed.
4. §12: No new topic creation after round 1.

---

## X38-D-03 / X38-D-15

Confirmed Converged. No new dispute. Carrying forward the round-2 resolutions
exactly as Codex restated them (`round-3_reviewer-reply.md:47-53`).

---

## PART A — STEEL-MAN ATTEMPT

### X38-D-16: Campaign transition guardrails

**Steel-man for Codex's position** (biconditional router overreaches; D-16
remains Open):

The Round 3 biconditional — `protocol unchanged ↔ corrective rerun`,
`protocol changed ↔ HANDOFF` — claims more than the authority supports.
Three arguments make this the strongest available challenge:

(a) `PLAN.md:502-503` gives `protocol có bug nghiêm trọng cần fix rồi re-run`
as a rationale for exceeding the same-file ceiling. This is a case where
protocol code changes but the text frames the action as a rerun, not a HANDOFF.
The biconditional predicts HANDOFF for any protocol change; the authority gives
a counter-example.

(b) The distinction I drew in Round 3 between "infrastructure bug" and
"methodology bug" (`round-3_author-reply.md:124-132`) assumes a semantic
classifier that does not yet exist. Topic 015 / F-17 owns semantic change
classification and explicitly leaves `Protocol logic (gating, selection) →
Case-by-case` unresolved
(`debate/015-artifact-versioning/findings-under-review.md:98`). Without that
classifier, the biconditional is unfalsifiable — you cannot test whether a
given protocol code change preserves or alters "protocol identity."

(c) My own phrasing — "operationally testable once Topic 003 defines protocol
content" (`round-3_author-reply.md:163`) — concedes the mechanism is deferred.
A deferred mechanism is not an operationalized router.

**Concession (evidence-backed, §8)**: The biconditional was too strong.
`PLAN.md:502-503` is genuine counter-evidence: a protocol bug fix changes
protocol code yet the authority treats it as a rerun justification, not a
HANDOFF trigger. My Round 3 argument assumed the semantic classifier was
available to distinguish "identity-preserving fix" from "identity-changing
methodology shift." That classifier is unresolved work in Topic 015 / F-17.
I drop the biconditional.

**Why the steel-man does not fully hold** — three points survive:

1. **The one-way rule is not contested and is substantive.** Both sides accept:
   a protocol identity change cannot remain within the same campaign
   (`round-3_reviewer-reply.md:94-95`: "protocol-changing fixes cannot be
   treated as an in-place continuation"). This follows directly from the
   campaign axiom (`design_brief.md:96-98`: `protocol cố định`). The one-way
   rule is not the biconditional — it says "if protocol identity changes, then
   new campaign boundary." It does not claim the reverse. But it IS a
   falsifiable constraint: any transition that changes protocol identity yet
   does not create a new campaign is non-compliant.

2. **The boundary-case mechanism already exists in the authority.**
   `PLAN.md:502-504` does not merely provide a counter-example — it provides
   the resolution for that counter-example. Three requirements are established:
   (a) exceeding the same-file ceiling requires **explicit human override**
   with specific justification; (b) every campaign must **declare its purpose**:
   `convergence audit hay corrective re-run?` (`PLAN.md:504`); (c) same-file
   methodological tightening does not create clean OOS evidence
   (`PLAN.md:505-506`). These are not prose — they are mandatory governance
   steps. A protocol bug fix that the human researcher classifies as
   "corrective rerun" is handled by declaration + override. A protocol change
   that the human researcher classifies as methodology gap triggers HANDOFF
   with dossier. The "router" for boundary cases is human judgment with
   mandatory declaration, not an automated classifier.

3. **The dependency on Topic 015 / F-17 is a cross-topic tension, not a D-16
   blocker.** D-03 froze required properties while deferring implementation
   shape to architecture spec. D-15 froze three scopes while deferring
   convergence methodology to Topic 013. By the same pattern, D-16 can freeze
   the boundary structure while deferring the automated semantic classifier to
   Topic 015 / F-17. What D-16 freezes is operational without the classifier:
   clear cases are resolved by the one-way rule; boundary cases are resolved
   by mandatory declaration and human override. What Topic 015 / F-17 will
   later provide is automation support — a welcome enhancement, but not a
   prerequisite for D-16's resolution to be operational.

**Revised resolution** (biconditional dropped, boundary-case mechanism added):

```
HANDOFF law (Topic 001 freezes):
  failure_modes:    {invalid_run, corrective_rerun, genuine_HANDOFF, new_data_restart}
  one_way_rule:     protocol_identity_change → new campaign boundary
  clear_cases:
    methodology_change (new search hypothesis)   → HANDOFF with dossier
    infrastructure_fix (no search change)         → corrective rerun
  boundary_cases:
    protocol_bug_fix (ambiguous)                  → mandatory declaration (PLAN.md:504)
                                                    + human override (PLAN.md:502)
  HANDOFF_package:
    trigger:        one of {convergence_stall, methodology_gap}
    principle:      single principal hypothesis
    dossier:        {convergence_summary, gap_evidence, proposed_change,
                     firewall_ref (→ Topic 002)}
    bounded_scope:  change budget required — exact numbers NOT frozen by 001

  deferred:
    semantic_classifier (automated detection)     → Topic 015 / F-17
    protocol_content (what constitutes protocol)  → Topic 003
    convergence_stall_thresholds                  → Topic 013
    content_gate_at_boundary                      → Topic 002
    bounded_recalibration_decisions                → Topic 016
```

The revised resolution is weaker than Round 3 (no biconditional) but stronger
than Round 2 (adds one-way rule + boundary-case mechanism). It handles every
transition type: clear cases by rule, boundary cases by mandatory declaration
and human authority. The structure is falsifiable: a transition that fails to
declare its purpose is non-compliant; a declaration without justification is
non-compliant; a protocol identity change without new campaign creation is
non-compliant.

**Proposed status**: Open — proposing convergence. Codex's §7(c) confirmation
is required. Per `debate/rules.md:40`, the status remains Open until then.

---

## Cross-topic tensions (updated)

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 007 (philosophy) | X38-D-01 | F-01 constrains campaign stop conditions: `NO_ROBUST_IMPROVEMENT` must be valid exit | 007 CLOSED; constraint inherited, 001 owns operationalization |
| 002 (firewall) | X38-D-04 | Firewall determines what can flow at HANDOFF — HANDOFF dossier references firewall, does not duplicate it | 002 owns content gate; 001 owns HANDOFF trigger/dossier/principle |
| 003 (protocol-engine) | — | Protocol content definition determines what "protocol identity" means; D-16 one-way rule depends on this but does not require it to be operational (human judgment substitutes) | 003 owns protocol content; 001 owns boundary rule |
| 010 (clean-oos) | X38-D-12, X38-D-21 | Clean OOS depends on campaign model defining Phase 1 exit criteria; new-data restart is Phase transition (010), not HANDOFF (001) | 010 owns certification; 001 defines campaign-level verdicts |
| 013 (convergence) | F-15 scoping | Convergence stall detection triggers HANDOFF; metric scoping defines convergence analysis boundaries; exact thresholds and session minimums are convergence-algorithm outputs | 013 owns convergence methodology + exact thresholds; 001 provides scope definitions + HANDOFF vocabulary |
| 015 (artifact-versioning) | F-17 | Semantic change classifier determines which protocol code changes preserve vs alter protocol identity; D-16 boundary-case mechanism uses human judgment until classifier is available | 015 owns classifier; 001 owns boundary rule + declaration mechanism |
| 016 (bounded-recalibration) | C-04, C-12 | Cross-campaign scope defined by 001; recalibration decisions using that scope owned by 016 | 016 owns decision; 001 provides HANDOFF mechanism + third scope definition |

---

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-D-03 | Freeze required campaign properties: methodology boundary, HANDOFF law, convergence scope, lineage. Container shape and numeric floors deferred | Judgment call | Converged | A first-class campaign lifecycle object is required to enforce the methodology boundary by construction | Campaign-tier verdicts prove grouping need, but `design_brief` / `PLAN` still leave thinner shapes open and Topic 013 owns numeric convergence floors |
| X38-D-15 | Freeze three scopes: session, campaign, cross-campaign/HANDOFF. V1 third scope is narrow transition justification + lineage accounting (MK-17 shadow-only). Reset at scope boundaries | Thiếu sót | Converged | Two scopes map 1:1 to Topic 007's two verdict tiers; third scope deferred to 016 | Verdict tiers ≠ metric tiers (different semantic axis); F-15 already states x38-native third scope; 016 is downstream of 001 |
| X38-D-16 | HANDOFF law: four failure modes, one-way rule (protocol identity change → new campaign), HANDOFF package (triggers, single hypothesis, dossier, bounded scope). Boundary cases (protocol bug fix) resolved by mandatory declaration + human override (`PLAN.md:502-504`). Biconditional dropped. Semantic classifier deferred to Topic 015/F-17 | Thiếu sót | Open | Biconditional router (protocol unchanged ↔ rerun, protocol changed ↔ HANDOFF) operationalizes the transition boundary using campaign axioms | `PLAN.md:502-503` gives protocol bug fix as counter-evidence to biconditional; semantic classifier needed for the distinction is unresolved in Topic 015/F-17; "once Topic 003 defines Y" is a deferral admission. Steel-man partially holds: biconditional dropped. Does not fully hold: one-way rule survives uncontested, boundary-case mechanism exists in `PLAN.md:502-504`, Topic 015 dependency is cross-topic tension not D-16 blocker |
