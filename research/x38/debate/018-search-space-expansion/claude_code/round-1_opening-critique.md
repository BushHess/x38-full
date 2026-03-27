# Round 1 — Opening Critique: Search-Space Expansion

**Topic**: 018-search-space-expansion
**Author**: claude_code
**Date**: 2026-03-27
**Scope**: SSE-D-01 (Lane ownership), SSE-D-02/03 (Bounded ideation / cold-start),
           SSE-D-04 (Breadth-expansion contract), SSE-D-05 (Surprise lane),
           SSE-D-06 (Cell + equivalence), SSE-D-07 (3-layer lineage),
           SSE-D-08 (Contradiction memory), SSE-D-09 (Multiplicity control),
           SSE-D-10 (Domain-seed hook), SSE-D-11 (APE v1 scope)
**Input documents**:
  - `research/x38/AGENTS.md`
  - `research/x38/x38_RULES.md`
  - `research/x38/docs/online_vs_offline.md`
  - `research/x38/docs/design_brief.md`
  - `research/x38/PLAN.md`
  - `research/x38/EXECUTION_PLAN.md`
  - `research/x38/debate/rules.md`
  - `research/x38/debate/prompt_template.md`
  - `research/x38/debate/debate-index.md`
  - `research/x38/debate/018-search-space-expansion/README.md`
  - `research/x38/debate/018-search-space-expansion/findings-under-review.md`
  - `research/x38/debate/018-search-space-expansion/final-resolution.md` [extra-canonical]
  - `research/x38/debate/018-search-space-expansion/closure-audit.md` [extra-canonical]
  - `research/x38/docs/search-space-expansion/request.md`
  - `research/x38/docs/search-space-expansion/debate/claude/claude_propone.md` [extra-canonical]
  - `research/x38/docs/search-space-expansion/debate/codex/codex_propone.md` [extra-canonical]
  - `research/x38/docs/search-space-expansion/debate/gemini/gemini_propone.md` [extra-canonical]
  - `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_propone.md` [extra-canonical]
  - `research/x38/docs/search-space-expansion/debate/claude/claude_debate_lan_5.md` [extra-canonical]
  - `research/x38/docs/search-space-expansion/debate/claude/claude_debate_lan_6.md` [extra-canonical]
  - `research/x38/docs/search-space-expansion/debate/codex/codex_debate_lan_5.md` [extra-canonical]
  - `research/x38/docs/search-space-expansion/debate/codex/codex_debate_lan_6.md` [extra-canonical]
  - `research/x38/docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` [extra-canonical]
  - `research/x38/docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` [extra-canonical]
  - `research/x38/docs/search-space-expansion/debate/gemini/gemini_debate_lan_6.md` [extra-canonical]
  - `research/x38/debate/004-meta-knowledge/final-resolution.md` (MK-17 shadow-only)
  - `research/x38/debate/002-contamination-firewall/final-resolution.md`

---

## Preamble

I write as the architect opening the standard 2-agent re-debate for Topic 018
(Search-Space Expansion). This topic addresses the discovery gap in x38: the
framework, as designed in `design_brief.md`, is strong on validation and
certification (8-stage pipeline, holdout, WFO) but has no mechanism for
generating novel features or recognizing unexpected results. The VDO origin
story (`request.md`) — an accidental AI-assisted discovery with no preserved
prompt, later proven across 16/16 timescales — is the motivating case.

Per `debate/rules.md` §5, the burden of proof lies with whoever proposes
changing the current design. The current design (`design_brief.md`) is silent
on discovery mechanisms. Therefore the burden here is on the *proposer* of each
SSE-D-* mechanism to show it is *necessary* (Thiếu sót) or that its absence
is a *design flaw* (Sai thiết kế). For issues classified as Judgment call,
I evaluate whether the tradeoffs are correctly identified and whether the
proposed resolution is well-grounded.

Topic 018 has 10 Open Issues (SSE-D-01 through SSE-D-11), each with its own
issue ID. A prior 4-agent debate (claude_code, codex, gemini, chatgptpro)
produced 7 rounds and 11 architectural decisions. **That debate was
extra-canonical** — not per `x38_RULES.md` §5 which specifies 2 canonical
participants (claude_code + codex). Per the reopening decision (2026-03-26),
prior Converged status is non-authoritative. I treat the prior debate archive
(`docs/search-space-expansion/debate/`) as input evidence, evaluating each
OI independently on its merits.

I assess the prior debate archive as substantively rich — 7 rounds across 4
agents produced thorough exploration of the design space, with multiple
positions tested and rejected. Several decisions reached genuine substance
alignment across all 4 agents. Where the prior debate achieved authentic
convergence through evidence and steel-manning, I expect the standard re-debate
to confirm quickly. Where I identify gaps, under-specified boundaries, or
consistency tensions, I challenge explicitly.

---

## SSE-D-01: Pre-lock generation lane ownership — ACCEPT with amendment

### Position

The prior debate correctly concluded that discovery mechanisms should fold into
6 existing topics (006/015/017/013/008/003) rather than creating a standalone
Topic 018 umbrella. This conclusion was unanimous by R2 — Claude withdrew the
Topic 018 proposal after ChatGPT Pro R1 argued folding is more tractable and
Codex R2 confirmed existing topic scopes already cover the substance
[extra-canonical: `chatgptpro/chatgptpro_propone.md`, `codex/codex_debate_lan_2.md`].

**Key argument**: The ownership split is architecturally sound because discovery
decomposes cleanly along existing topic boundaries: generation semantics (006),
lineage/provenance (015), coverage/surprise/proof (017), correction (013),
identity vocabulary (008), stage wiring (003). No residual design object was
identified that requires a cross-cutting umbrella topic. The closure trigger —
"new topic only if downstream closure report reveals explicit unresolved gap" —
provides a safety valve without prematurely creating infrastructure.

**However**, the ownership split at the architecture level is *directional
routing*, not *confirmed downstream acceptance*. Codex R6 correctly noted that
Claude R6's CL-20 object boundary list was "directional routing proposal, not
authoritative inventory" [extra-canonical: `codex/codex_debate_lan_6.md`:124,167].
The key risk is not that the split is wrong, but that downstream topics absorb
the routing without explicitly confirming they own the objects. This could
create orphaned obligations.

**Proposed amendment**: ACCEPT the fold, but require that the `final-resolution.md`
for Topic 018 include a machine-checkable routing table with columns
`{object, source_SSE_D, routed_to_topic, downstream_issue_id}`. Each routed
object must appear as an issue or sub-issue in the downstream topic's
`findings-under-review.md`. Provisional routings already exist (SSE-07→015,
SSE-08→015/017, SSE-09→013, SSE-04-IDV→008 per `debate-index.md`). The
amendment formalizes the requirement: if a downstream topic closes without
addressing a routed object, the orphan triggers the safety valve (new topic).

### Classification: Judgment call

---

## SSE-D-02/03: Bounded ideation + conditional cold-start — ACCEPT with amendment

### Position

The prior debate's resolution of bounded ideation (SSE-D-02) and grammar
depth-1 cold-start (SSE-D-03) is well-grounded and I accept the substance.

**On SSE-D-02** (bounded ideation replacing SSS): The 4 hard rules —
(1) results-blind, (2) compile-only, (3) OHLCV-only, (4) provenance-tracked —
are the correct response to the contamination risk that killed SSS. Claude
self-identified the SSS contamination vector in R1 ("AI seeing registry =
implicit negative priors") [extra-canonical: `claude/claude_debate_lan_1.md` §5.4].
ChatGPT Pro R2 declared SSS "dead architecturally"
[extra-canonical: `chatgptpro/chatgptpro_debate_lan_2.md`]. The bounded ideation
lane is strictly pre-lock, compile-only output, and results-blind — this
preserves the contamination firewall (Topic 002, X38-D-04) while allowing the
"happy accident" generation that `request.md` motivates.

**On SSE-D-03** (conditional cold-start): ChatGPT Pro R4's "conditional
cold-start law" correctly resolved the mandatory-vs-optional tension
[extra-canonical: `chatgptpro/chatgptpro_debate_lan_4.md`:107-110].
`grammar_depth1_seed` is a mandatory *capability* with conditional *activation*
as default when registry is empty. `registry_only` is the conditional path for
importing frozen non-empty registries.

**Key argument**: Both decisions are necessary to fill the gap identified in
`request.md`: x38 had no mechanism for "chủ động tạo ra những lần 'vô tình'"
(proactively creating "accidents"). Bounded ideation provides the generation
lane; conditional cold-start ensures an empty registry gets populated.

**However**, I identify two under-specifications that warrant tightening:

1. **"Results-blind" boundary case**: Hard rule 1 says AI sees OHLCV only, not
   "registry or prior results." But the grammar definition itself (the operator
   table, composition rules, depth limits) is a form of structural knowledge.
   When a researcher writes a grammar, they are implicitly encoding domain
   knowledge about what combinations are worth exploring. The rule correctly
   blocks *empirical result contamination* (seeing which features performed
   well), but the line between "domain knowledge encoded in grammar" and
   "structural prior from past results" needs sharper demarcation. This is
   especially relevant for warm-start campaigns where the grammar was refined
   based on outcomes from prior campaigns on different data.

2. **"Compile-only" operational definition**: The rule says output is
   "spec/proposal, not running code." In practice, the boundary between
   "compiled manifest" and "runnable code" depends on the feature DSL design
   (Topic 006 scope). If the DSL is expressive enough, a compiled manifest *is*
   effectively runnable code. The bounded ideation contract should specify that
   the compile pass is a *syntax + admissibility* check, not an *evaluation*
   check — i.e., the compile pass verifies the feature is well-formed and within
   grammar bounds, but does not compute any performance metric. This
   distinction is critical for the contamination firewall.

**Proposed amendment**: ACCEPT both decisions. Add two clarifications:
(a) "Results-blind" means the ideation agent receives no empirical results
(backtest metrics, feature rankings, performance data) from any campaign — but
grammar definitions themselves are not considered "results" provided they were
not reverse-engineered from empirical outcomes. Cross-campaign grammar
refinement is a meta-knowledge question (MK-17 ceiling applies).
(b) "Compile-only" means the compile pass verifies syntax, type conformance,
and admissibility (within grammar bounds) — it MUST NOT evaluate performance
or compute any metric that could leak information about the feature's quality.

### Classification: Thiếu sót

---

## SSE-D-04: 7-field breadth-activation contract — ACCEPT with amendment

### Position

The 7-field breadth-activation interface contract is the most mature artifact
from the prior debate and I accept its structure. The requirement that a
protocol MUST declare all 7 fields before breadth activation is well-motivated:
it prevents breadth expansion (scanning many candidates) without the
infrastructure to evaluate, deduplicate, and correct for multiplicity.

The 7 fields and their downstream owners are:

| # | Field | Owner |
|---|-------|-------|
| 1 | `descriptor_core_v1` | 017 |
| 2 | `common_comparison_domain` | 013 |
| 3 | `identity_vocabulary` | **UNRESOLVED** (008 or 013 TBD) |
| 4 | `equivalence_method` | 013 + 008 |
| 5 | `scan_phase_correction_method` | 013 |
| 6 | `minimum_robustness_bundle` | 017 + 013 |
| 7 | `invalidation_scope` | 015 |

**Key argument**: This interface contract is the right architectural pattern —
it separates the *obligation* (which fields must exist) from the *content*
(what values those fields take), allowing Topic 018 to lock the interface while
downstream topics lock the semantics. This is a standard separation of concerns
pattern. Evidence: Codex R5 demanded a concrete field list rather than abstract
direction [extra-canonical: `codex/codex_debate_lan_5.md`:170-175]; Claude R6
reconciled CL-19's 6-point framing with Codex's 7-field naming
[extra-canonical: `claude/claude_debate_lan_6.md`:76-98].

**However**, field 3 (`identity_vocabulary`) has an acknowledged owner gap.
Claude R7 correction noted: "Candidate-level `identity_vocabulary` owner = TBD
by synthesis" — Topic 008 covers protocol/campaign/session identity axes per
X38-D-13, but candidate-level equivalence vocabulary may fall outside 008's
current scope [extra-canonical: `codex/codex_debate_lan_6.md`:124,167;
`final-resolution.md` SSE-D-04 correction note]. Topic 008 has since CLOSED
(2026-03-27 per `debate-index.md`) — if 008 did not address candidate-level
`identity_vocabulary`, this is a confirmed orphan.

**Proposed amendment**: ACCEPT the 7-field contract. Require explicit resolution
of the field 3 owner gap: either (a) confirm Topic 008's closure addressed it,
(b) assign it to Topic 013 (which owns `equivalence_method` and
`common_comparison_domain` — both related), or (c) open a targeted issue in
whichever downstream topic is most appropriate. An unresolved owner for a
mandatory interface field is a structural gap, not a minor bookkeeping detail.

### Classification: Thiếu sót

---

## SSE-D-05: Recognition stack minimum — ACCEPT

### Position

The recognition topology (surprise_queue → equivalence_audit → proof_bundle →
freeze) and minimum inventory (5 anomaly axes + 5-component proof bundle) are
well-grounded and I accept this decision without amendment.

**Key argument**: The VDO origin story is the primary evidence. VDO's value was
16/16 timescale consistency (cross-resolution robustness), not peak Sharpe.
ChatGPT Pro's "consistency motif" insight — that a peak-score-only ranking
would have killed VDO — motivates the anomaly axes design
[extra-canonical: `chatgptpro/chatgptpro_propone.md`]. The 5 anomaly axes
(decorrelation outlier, plateau width champion, cost stability, cross-resolution
consistency, contradiction resurrection) capture distinct dimensions of
"unexpectedness" that peak-score rankings miss. The 5-component proof bundle
(nearest_rival_audit, plateau_stability_extract, cost_sensitivity_test,
ablation_or_perturbation, contradiction_profile) ensures recognized surprises
are substantiated, not noise.

The evidence hierarchy supports this: project-specific empirical evidence
(V4→V8, x37) outranks general theory per `rules.md` §6. The X21 study
[extra-archive] showed entry features had zero predictive power (IC = -0.039
OOS), validating the decision to use anomaly axes rather than IC-based screening
for recognition.

**However**, I note one observation (not rising to challenge level): the 5
anomaly axes are specified as a *minimum* inventory, not a closed set. The
topology correctly allows additional axes to be added. The queue admission rule
(≥1 non-peak-score axis) ensures that peak-score-only candidates do not
dominate the surprise queue. Exact thresholds are correctly deferred to
017/013.

### Classification: Thiếu sót

---

## SSE-D-06: Hybrid equivalence — ACCEPT

### Position

The 2-layer deterministic hybrid equivalence (structural pre-bucket + behavioral
nearest-rival audit) was the major substantive dispute of the prior debate and
I accept the resolution as correct.

**Key argument**: Equivalence determination requires both structural and
behavioral comparison because the two capture different failure modes:
- Structural-only (AST-hash + parameter distance) misses *economic* duplicates:
  two features with different implementations but ρ > 0.99 on paired returns
  are economically redundant but structurally distinct.
- Behavioral-only misses *syntactic* duplicates: features with identical logic
  but different parameter names that happen to produce slightly different returns
  due to rounding or timing would not cluster as duplicates.

The hybrid preserves determinism — both layers are fully deterministic (same
data + code + seed = same result). Gemini's original AST-only position was
motivated by a valid concern (behavioral equivalence introduces
evaluation-dependency: changing cost model changes equivalence classification),
but this concern is addressed by anchoring the behavioral layer to the
`common_comparison_domain` (SSE-D-04 field 2), which is fixed per protocol.
Gemini withdrew AST-only in R6 and accepted the hybrid
[extra-canonical: `gemini/gemini_debate_lan_6.md`:33-37,98-100].

The no-LLM constraint is essential: equivalence must be machine-deterministic
for reproducibility. This aligns with `online_vs_offline.md` — the offline
paradigm requires no AI in the execution path.

### Classification: Thiếu sót

---

## SSE-D-07: 3-layer lineage — ACCEPT (routed to 015)

### Position

The semantic split into `feature_lineage`, `candidate_genealogy`, and
`proposal_provenance` is accepted without amendment. The split is motivated
by different invalidation semantics: changes to feature compilation invalidate
`feature_lineage`; changes to architecture composition invalidate
`candidate_genealogy`; audit trail changes to `proposal_provenance` never
invalidate the replay path.

**Key argument**: 4/4 agents aligned on this split by R3
[extra-canonical: `codex/codex_debate_lan_3.md` OI-04;
`chatgptpro/chatgptpro_debate_lan_3.md` OI-04]. Field enumeration and the
invalidation matrix are correctly routed to Topic 015 (artifact versioning),
which owns `X38-D-14` and `X38-D-17`. The semantic split is an architecture
decision (belongs here); the field details are a versioning decision (belongs
in 015).

This is a clean routing. Downstream issue `X38-SSE-07` exists in Topic 015's
`findings-under-review.md`.

### Classification: Thiếu sót

---

## SSE-D-08: Contradiction registry — ACCEPT with probe

### Position

The contradiction registry as a descriptor-level, shadow-only store bounded by
the MK-17 ceiling is accepted. The routing (storage contract → 015, consumption
semantics → 017) is architecturally clean.

**Key argument**: MK-17 (from CLOSED Topic 004) mandates that same-dataset
learned priors remain shadow-only — they cannot become active priors for the
same data. The contradiction registry stores cases where a candidate was
rejected or underperformed, preserving the information without allowing it to
bias future search. This is the correct governance response: don't discard
negative evidence, but don't let it contaminate fresh evaluation either.

**However**, I probe a consistency question between SSE-D-08 and SSE-D-05.
The 5th anomaly axis in SSE-D-05 is "contradiction resurrection" — it flags
candidates that revive prior negative evidence. This axis *consumes*
contradiction registry data. If the contradiction registry is shadow-only
(SSE-D-08), and an anomaly axis uses it to preferentially flag candidates
(SSE-D-05), then the system is using same-dataset negative priors to influence
the *recognition* path, even though it doesn't influence the *generation* or
*evaluation* path.

The question is: does contradiction resurrection via the surprise queue violate
MK-17's shadow-only ceiling? I argue it does not, provided:
(a) Contradiction resurrection only affects *queue admission priority*, not
    evaluation scores or gate decisions.
(b) The proof bundle for such candidates is identical to any other candidate —
    the contradiction flag does not lower the evidence bar.
(c) The contradiction_profile component of the proof bundle explicitly documents
    the prior negative evidence, making the prior visible rather than hidden.

This interpretation is consistent with MK-17's intent (prevent hidden bias)
while preserving the value of accumulated negative evidence. But the
interaction must be explicitly documented in the final resolution to prevent
future misinterpretation. Topic 017 (ESP) owns the consumption semantics and
should formalize this constraint.

**Proposed amendment**: ACCEPT with explicit documentation that contradiction
resurrection operates at queue-priority level only, not at evaluation or gating
level. Route this constraint to Topic 017 (X38-SSE-08-CON) as a binding
clarification.

### Classification: Judgment call

---

## SSE-D-09: Multiplicity control coupling — ACCEPT (routed to 013)

### Position

The coupling of multiplicity control to the breadth-activation contract via
SSE-D-04 field 5 (`scan_phase_correction_method`) is accepted without
amendment. The exact correction formula (Holm/FDR/cascade) is correctly
deferred to Topic 013 (convergence analysis), which owns the statistical
methodology.

**Key argument**: Breadth expansion introduces many candidates simultaneously,
which creates a multiple comparisons problem. The requirement to declare a
correction method before activating breadth is a structural safeguard — it
prevents the framework from generating many candidates and then picking the
best without adjusting for the number tested. This is standard quantitative
research practice.

The decision to defer the *exact* formula is correct: the choice between Holm,
FDR, or cascade correction depends on assumptions about the dependency structure
of candidates, which Topic 013 is better positioned to evaluate. ChatGPT Pro
R4 self-corrected an earlier attempt to lock Holm as the default
[extra-canonical: `chatgptpro/chatgptpro_debate_lan_4.md`:57], recognizing
that the evidence base was insufficient to choose the specific formula at this
level.

Downstream issue `X38-SSE-09` exists in Topic 013's `findings-under-review.md`.

### Classification: Thiếu sót

---

## SSE-D-10: Domain-seed = optional provenance hook — ACCEPT

### Position

Accepted without amendment. Domain-seed as an optional provenance hook (not a
core mechanism with replay semantics, session format, or budget allocation) is
the correct scope for v1.

**Key argument**: The prior debate effectively killed stronger alternatives.
Claude's CDAP (Cross-Domain Analogy Prompting) and ChatGPT Pro's Domain Seed
Prompting both proposed domain catalogs as core infrastructure. By R3, all
agents agreed that domain knowledge belongs in authoring provenance, not in
replay paths or runtime infrastructure
[extra-canonical: `chatgptpro/chatgptpro_debate_lan_4.md` CL-11]. The hook
pattern preserves composition provenance (if a researcher was inspired by
a concept from signal processing, that fact is recorded in
`proposal_provenance`) without requiring the framework to maintain a domain
ontology, replay engine, or cross-domain matching system.

This is an appropriate v1 boundary: minimal infrastructure that preserves
information for future expansion. If v2+ needs a domain catalog, the
provenance trail exists to motivate it.

### Classification: Judgment call

---

## SSE-D-11: APE v1 = parameterization only — ACCEPT

### Position

Accepted without amendment. APE (Automated Protocol Expansion) in v1 is
limited to template parameterization and compile-time ideation — no free-form
code generation.

**Key argument**: The correctness guarantee is absent for AI-generated code.
If APE generates arbitrary strategy code, the framework cannot verify that the
code implements the intended logic without a formal verification system that
does not exist. Template parameterization constrains the output to known
templates with variable parameters, where correctness reduces to type-checking
and bound-checking of the parameters — a tractable verification problem.

Free-form code generation creates two risks:
(1) **Correctness**: generated code may contain subtle bugs (lookahead,
    survivorship bias, off-by-one in bar alignment) that pass compile checks
    but produce invalid backtest results.
(2) **Contamination**: if the code generation model has been trained on or
    exposed to backtest results, the generated code may implicitly encode
    those results, violating the contamination firewall.

Both risks are mitigated by the parameterization constraint: templates are
human-authored and verified, parameters are bounded by the grammar. This aligns
with `online_vs_offline.md` — offline execution must be deterministic and
auditable.

Depth-2+ grammar, GA/mutation, and code generation are correctly deferred to
v2+ when correctness infrastructure may exist.

### Classification: Thiếu sót

---

## Summary

### Accepted (near-convergence candidates)

The following issues have strong substance alignment from the prior debate and
I expect rapid convergence in the standard re-debate:

- **SSE-D-05** (Recognition stack minimum): Accepted without amendment.
  Well-grounded in VDO evidence and project-specific empirical results.
- **SSE-D-06** (Hybrid equivalence): Accepted without amendment.
  Major prior dispute fully resolved; Gemini withdrawal was genuine.
- **SSE-D-07** (3-layer lineage): Accepted, cleanly routed to 015.
- **SSE-D-09** (Multiplicity control): Accepted, cleanly routed to 013.
- **SSE-D-10** (Domain-seed hook): Accepted without amendment.
- **SSE-D-11** (APE v1 scope): Accepted without amendment.

### Challenged (need debate)

The following issues are accepted in substance but have specific amendments
or probes that require Codex's response before convergence:

- **SSE-D-01** (Lane ownership): Amendment — machine-checkable routing table
  required; orphan detection mechanism must be explicit.
- **SSE-D-02/03** (Bounded ideation / cold-start): Amendment — "results-blind"
  boundary sharpening (grammar ≠ results) and "compile-only" operational
  definition (syntax + admissibility, not evaluation).
- **SSE-D-04** (Breadth-activation contract): Amendment — field 3
  (`identity_vocabulary`) owner gap must be resolved, especially given
  Topic 008 has now CLOSED.
- **SSE-D-08** (Contradiction memory): Probe — contradiction resurrection
  anomaly axis must be explicitly constrained to queue-priority only,
  not evaluation/gating, to maintain MK-17 consistency.

---

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| SSE-D-01 | Pre-lock generation lane ownership | Judgment call | Open | "Downstream chưa echo owner split → routing chỉ là slogan" | Valid concern — amendment adds machine-checkable routing table + orphan trigger. Not a rejection of the fold, but a structural safeguard. |
| SSE-D-02 | Bounded ideation replaces SSS | Thiếu sót | Open | "results-blind quá strict — grammar encode domain knowledge từ prior campaigns" | Grammar definitions are not empirical results; amendment clarifies boundary. MK-17 governs cross-campaign grammar refinement. |
| SSE-D-03 | Grammar depth-1 conditional cold-start | Thiếu sót | Open | "Mandatory every campaign = lãng phí khi registry đã non-empty" | Correct — conditional activation resolves this. Amendment on compile-only definition is orthogonal to mandatory-vs-optional. |
| SSE-D-04 | 7-field breadth-activation contract | Thiếu sót | Open | "7/7 identified and routed → interface đã đủ" | Interface identified but field 3 owner unresolved. 008 CLOSED — orphan risk real. Amendment requires explicit owner assignment. |
| SSE-D-05 | Recognition stack minimum | Thiếu sót | Open | — | Near-convergence. No substantive challenge from architect. |
| SSE-D-06 | Hybrid equivalence | Thiếu sót | Open | "AST-hash + parameter distance đủ (context-free, stable)" | Economic duplicates exist that structural comparison misses. Hybrid preserves determinism. Gemini R6 withdrew. |
| SSE-D-07 | 3-layer lineage | Thiếu sót | Open | "Field enumeration chưa xong → issue phải active ở đây" | Semantic split locked; field enumeration = 015 scope. Clean routing confirmed (X38-SSE-07 exists in 015). |
| SSE-D-08 | Contradiction registry | Judgment call | Open | "Shadow-only constraint kills contradiction resurrection utility" | Resurrection operates at queue-priority only, not evaluation/gating. MK-17 intent (prevent hidden bias) preserved. Requires explicit documentation. |
| SSE-D-09 | Multiplicity control coupling | Thiếu sót | Open | "Coupling → default law phải khóa ngay" | Coupling locked; exact formula is a 013 decision, not 018. Clean routing confirmed (X38-SSE-09 exists in 013). |
| SSE-D-10 | Domain-seed = optional hook | Judgment call | Open | "Cross-domain cross-pollination là core mechanism" | Composition provenance preserves trail without infrastructure. Hook pattern = correct v1 scope. |
| SSE-D-11 | APE v1 = parameterization only | Thiếu sót | Open | "Code generation tạo structural innovation không thể đạt qua parameterization" | Correctness guarantee absent; parameterization is tractable verification. Code gen = v2+ when verification infra exists. |
