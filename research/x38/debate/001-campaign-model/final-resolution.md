# Final Resolution — Campaign Model

**Topic ID**: X38-T-01
**Opened**: 2026-03-22
**Closed**: 2026-03-23
**Rounds**: 6 / 6 (max_rounds_per_topic reached per §13)
**Participants**: claude_code (author), codex (reviewer)

---

## Summary

Topic 001 debated 3 findings (F-03, F-15, F-16) across 6 rounds.

**Final tally**: 2 Converged, 1 Judgment call (§14 → human researcher).
All 3 issues resolved. No open items.

**Round symmetry note (§14b)**: claude_code submitted 6 rounds, codex submitted
5 rounds. Codex did not respond to claude_code's round-6 author reply before
the human researcher decided D-16 via §14 Judgment call. Asymmetry accepted
because: (a) D-03 and D-15 were already Converged since round 2 — unaffected;
(b) D-16 was decided as Position C, a new position independent of both agent
positions A and B — Codex's round 6 response would not have changed the human's
decision; (c) Codex closure audit (`codex/closure-audit.md`) provides quality
assurance on the final artifacts, covering the review function that round 6
would have served.

---

## Decisions

| Issue ID | Finding | Resolution | Type | Round closed |
|----------|---------|------------|------|-------------|
| X38-D-03 | Campaign → Session model | Freeze required campaign properties over container shape; exact numeric floors to Topic 013 | Converged | R2 |
| X38-D-15 | Two cumulative scopes | Freeze three scopes (session, campaign, cross-campaign/HANDOFF); v1 third scope stays narrow | Converged | R2 |
| X38-D-16 | Campaign transition guardrails | Judgment call: Position C — structural HANDOFF law + routing contract matrix (see §Judgment below) | Judgment call | R6 → §14 |

---

## Key design decisions (for drafts/)

### Decision 1: Campaign as property set (D-03)

**Accepted position**: A campaign is defined by required properties: grouping
above sessions, shared protocol/dataset boundary, lineage, and HANDOFF law.
Exact container shape (first-class object vs lightweight grouping) deferred to
architecture spec. Numeric convergence floors deferred to Topic 013.

**Rejected alternative**: A first-class campaign lifecycle object is required to
enforce the methodology boundary by construction.

**Rationale**: Campaign-tier verdicts prove grouping need. The authority
(`design_brief.md:96-102`, `PLAN.md:445-451`) defines campaign contents while
leaving thinner container shapes open (`design_brief.md:115-118`,
`PLAN.md:491-494`). Topic 013 owns numeric convergence rules (`PLAN.md:974-975`).

### Decision 2: Three metric scopes (D-15)

**Accepted position**: Three scopes: session, campaign, and
cross-campaign/HANDOFF. V1 third scope stays narrow (transition justification +
lineage accounting, MK-17 shadow-only). Does not become an active empirical
ranking lane.

**Rejected alternative**: Two scopes mapping 1:1 to Topic 007's two
verdict-bearing tiers, with cross-campaign scope deferred to Topic 016.

**Rationale**: Verdict tiers are claim ceilings, not metric boundaries — two
different semantic axes. F-15 already states a third x38-native scope. Topic 016
is downstream of 001.

### Decision 3: Transition routing contract (D-16, Judgment call)

**Accepted position**: Position C — structural HANDOFF law + conservative
routing contract matrix. Neither Position A (Claude Code: structural law alone
suffices) nor Position B (Codex: must wait for Topic 015 classifier) fully
resolves the gap. Position C freezes a decision table that is sufficient for
spec drafting without requiring an automated classifier.

**Rejected alternatives**:
- Position A (claude_code): F-16 guardrails are answered by structural HANDOFF
  law; route classification is a cross-topic dependency, not a D-16 residual.
  *Too optimistic*: operator still lacks decision criteria for ambiguous cases.
- Position B (codex): F-16's core question is the corrective_re_run vs
  genuine_HANDOFF router; deferring route classification defers this mechanism.
  *Too blocking*: delays downstream topics (003, 016) unnecessarily; automated
  classifier is not required for human-operated V1.

**Rationale**: The debate correctly narrowed D-16 to a precise scope dispute
over 6 rounds. Both agents agreed on structural elements (one-way invariant,
HANDOFF package, same-data governance, four-route taxonomy). The sole dispute
was whether deferring route classification resolves or defers F-16. Position C
resolves this by freezing a routing contract that the operator can apply without
an automated classifier, while explicitly deferring the classifier to Topic 015.

**Key insight (human researcher)**: The debate conflated two axes — route/action
(what do you DO?) and purpose label (WHY?). Separating them eliminates the
ambiguity that prevented convergence. A corrective re-run is not a silent patch
within the same campaign — it is a new same-data corrective campaign, because
campaign = fixed dataset + fixed protocol (`design_brief.md:96-102`).

---

## §14 Judgment — X38-D-16: Campaign Transition Guardrails

**Status**: CLOSED via Judgment call (not Converged).
**decision_owner**: human researcher (per `debate/rules.md:70`, §15 default).

### Frozen in Topic 001

1. **Campaign definition**: fixed dataset + fixed protocol + N sessions +
   convergence analysis + meta-knowledge output (`design_brief.md:96-102`).
2. **One-way invariant**: `protocol_identity_change → new campaign boundary`.
3. **Same-data governance** (from `PLAN.md:500-506`): same-file ceiling with
   explicit human override, mandatory purpose declaration, same-file tightening
   ≠ clean OOS evidence.
4. **HANDOFF package**: triggers `{convergence_stall, methodology_gap}`, single
   principal hypothesis, dossier `{convergence_summary, gap_evidence,
   proposed_change, firewall_ref (→ Topic 002)}`, bounded scope (exact numbers
   to Topic 013).
5. **Transition routing contract** (matrix below).
6. **Burden of proof**: if protocol-identity preservation is not proven, do NOT
   use `corrective_re_run`. Default to HANDOFF.

### Transition-Routing Contract

| Evidence on frozen baseline | Claimed basis | Action | Campaign purpose |
|---|---|---|---|
| bit-identical / comment-only | n/a | no transition | n/a |
| results changed + proven defect + protocol identity preserved | defect correction | open same-data corrective campaign; invalidate affected scope and rerun | `corrective_re_run` |
| results changed + methodology/search/gating/objective changed | new hypothesis / methodology gap | open HANDOFF campaign | `convergence_audit` |
| ambiguous or preservation unproven | disputed | default to HANDOFF campaign | `convergence_audit` |
| new data appended / Clean OOS fail restart | n/a | new-data restart | n/a |

**Note on "results changed"**: refers to results relevant to the change scope —
trade log (engine changes), rankings (metrics changes), verdicts (protocol logic
changes). Consistent with F-17's semantic change classification table
(`debate/015-artifact-versioning/findings-under-review.md:92-99`).

**Note on proven defect + protocol identity change**: a proven defect that ALSO
changes protocol identity (e.g., feature computation formula fix that alters
effective strategy behavior) routes to row 4 (default HANDOFF), not row 2.
Row 2 requires ALL three conjuncts: results changed AND proven defect AND
protocol identity preserved.

### Campaign Purpose Labels

Per `PLAN.md:504`, every same-data campaign must declare one of two purposes:

- **`corrective_re_run`**: campaign corrects a proven defect without changing
  methodology intent. Protocol identity preserved.
- **`convergence_audit`**: encompasses (a) verifying independent session
  convergence on the same protocol (original V7 meaning,
  `PROMPT_FOR_V7_HANDOFF.md:17` [extra-archive]), AND (b) methodology
  advancement triggered by `methodology_gap`. Broadly: any same-data campaign
  that is NOT a corrective re-run.

The HANDOFF trigger vocabulary (`{convergence_stall, methodology_gap}`) provides
more precise operational routing than the binary purpose label. Purpose label is
a governance checkpoint (human declaration per `PLAN.md:504`); trigger field is
operational routing within the HANDOFF package.

### Deferred, Not Blocked

| What | Owner | Rationale |
|---|---|---|
| Protocol identity/version **schema** | Topic 008 (F-13: three identity axes) | 008 owns identity/version schema structure |
| Protocol **content** referenced by schema | Topic 003 (F-05: 8-stage pipeline) | 003 defines what constitutes "protocol" |
| Stop thresholds, same-data ceiling, sessions-per-campaign | Topic 013 (F-31: convergence methodology) | 013 owns numeric convergence rules |
| Evidence classes, invalidation scope | Topic 015 / F-17 (semantic change classification) | 015 owns classification; 001 consumes via routing contract |
| Recalibration exceptions | Topic 016 (bounded recalibration path) | 016 owns recalibration decisions |

**Scope boundary**: Topic 015 outputs evidence classes and invalidation scope.
Topic 001 maps those evidence classes to campaign actions via the routing
contract. Topic 015 does NOT own campaign routing semantics. Topic 001 does NOT
own the semantic diff engine.

---

## Agreed Elements (stable since Round 4, both agents)

These were never disputed and are carried forward as frozen law:

1. One-way invariant: `protocol_identity_change → new campaign boundary`
2. HANDOFF package: triggers, single hypothesis, dossier, bounded scope
3. Same-data governance: human override, mandatory declaration, evidence rule
4. Four route taxonomy: `{invalid_run, corrective_re_run, genuine_HANDOFF,
   new_data_restart}`
5. Route classification NOT frozen by Topic 001 as an automated mechanism —
   deferred to Topic 015/F-17

---

## Cross-topic tensions (final)

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 007 (philosophy) | X38-D-01 | F-01 constrains campaign stop conditions: `NO_ROBUST_IMPROVEMENT` must be valid exit | 007 CLOSED; constraint inherited, 001 owns operationalization |
| 002 (firewall) | X38-D-04 | Firewall determines what can flow at HANDOFF — HANDOFF dossier references firewall, does not duplicate it | 002 owns content gate; 001 owns HANDOFF trigger/dossier/principle |
| 003 (protocol-engine) | F-05 | Protocol content definition determines what "protocol identity" means; routing contract references it | 003 owns protocol content; 001 owns routing contract |
| 008 (architecture-identity) | F-13 | Identity/version schema determines how protocol_identity is tracked | 008 owns identity schema; 001 owns one-way invariant that consumes it |
| 010 (clean-oos) | X38-D-12, X38-D-21 | Clean OOS depends on campaign model defining Phase 1 exit criteria; new-data restart is Phase transition (010), not HANDOFF (001) | 010 owns certification; 001 defines campaign-level verdicts |
| 013 (convergence) | F-15, F-31 | Convergence stall detection triggers HANDOFF; metric scoping defines analysis boundaries; stop thresholds, same-data ceiling, sessions-per-campaign are convergence outputs | 013 owns convergence methodology + numeric thresholds; 001 provides scope definitions + HANDOFF vocabulary |
| 015 (artifact-versioning) | F-17 | Semantic change classification outputs evidence classes consumed by routing contract; invalidation scope determines "results changed" in the matrix | 015 owns evidence classes + invalidation scope; 001 owns campaign routing that consumes them |
| 016 (bounded-recalibration) | C-04, C-12 | Cross-campaign scope defined by 001; recalibration decisions using that scope owned by 016 | 016 owns recalibration decision; 001 provides HANDOFF mechanism + third scope definition |

---

## Complete Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-D-03 | Freeze required campaign properties over container shape: grouping above sessions, shared protocol/dataset boundary, lineage, and HANDOFF law; exact numeric floors stay in Topic 013 | Judgment call | **Converged** | A first-class campaign lifecycle object is required to enforce the methodology boundary by construction | Campaign-tier verdicts prove grouping need, but the authority still leaves thinner container shapes open and reserves numeric convergence rules for Topic 013 |
| X38-D-15 | Freeze three scopes: session, campaign, and cross-campaign/HANDOFF; v1 third scope stays narrow and does not become an active empirical ranking lane | Thiếu sót | **Converged** | Two scopes should map 1:1 to Topic 007's two verdict-bearing tiers, with cross-campaign scope deferred to 016 | Verdict tiers are claim ceilings, not metric boundaries; F-15 already states a third x38-native scope, and 016 is downstream of 001. No reset-law was frozen here |
| X38-D-16 | Transition routing contract: one-way invariant, HANDOFF package, same-data governance, 5-row routing matrix with burden of proof (default HANDOFF if ambiguous). Automated route classification deferred to 015/F-17 | Thiếu sót | **Judgment call** (§14) | Position A: structural HANDOFF law resolves F-16's guardrail gaps; Position B: route classification is F-16's core gap | Position C (human researcher): both A and B partially correct. A too optimistic (operator lacks criteria), B too blocking (delays downstream). Routing contract matrix fills the gap without requiring automated classifier. Two-axis separation (route/action vs purpose) resolves the ambiguity that prevented convergence |

---

## Unresolved tradeoffs (for human review)

No unresolved tradeoffs. D-03 and D-15 are fully Converged. D-16 is resolved
via Judgment call with a concrete routing contract — Position C resolves the
dispute between Position A and Position B rather than deferring it. The deferred
items (008 identity schema, 003 protocol content, 013 numeric thresholds, 015
evidence classes, 016 recalibration) are cross-topic dependencies with clear
ownership, not unresolved internal tradeoffs.

---

## Draft impact

| Draft | Sections affected | Action needed |
|-------|------------------|---------------|
| `architecture_spec.md` | Campaign model definition, scope hierarchy | Create — campaign properties, three scopes |
| `architecture_spec.md` | HANDOFF law + routing contract | Create — transition matrix, burden of proof, purpose labels |
| `architecture_spec.md` | Cross-topic interfaces | Create — 008 identity schema, 015 evidence classes consumed by routing contract |
| `meta_spec.md` | MK-17 same-dataset shadow-only | Update — reference campaign scope definitions from 001 |

---

**Topic 001 — CLOSED. Decisions signed off by human researcher.**
