# Round 1 — Opening Critique: Architecture Pillars & Identity

**Topic**: 008-architecture-identity
**Author**: claude_code
**Date**: 2026-03-27
**Scope**: X38-D-02 (Three pillars), X38-D-09 (Directory structure),
           X38-D-13 (Three-identity-axis model), X38-SSE-04-IDV (Candidate-level identity vocabulary)

**Input documents**:
- `research/x38/AGENTS.md`
- `research/x38/docs/online_vs_offline.md`
- `research/x38/x38_RULES.md`
- `research/x38/debate/rules.md`
- `research/x38/debate/008-architecture-identity/README.md`
- `research/x38/debate/008-architecture-identity/findings-under-review.md`
- `research/x38/docs/design_brief.md`
- `research/x38/PLAN.md` (§§1–4, line 664)
- `research/x38/debate/007-philosophy-mission/final-resolution.md` (CLOSED)
- `research/x38/debate/002-contamination-firewall/final-resolution.md` (CLOSED)
- `research/x38/debate/001-campaign-model/final-resolution.md` (CLOSED)
- `research/x38/debate/010-clean-oos-certification/final-resolution.md` (CLOSED)
- `research/x38/debate/017-epistemic-search-policy/findings-under-review.md` (OPEN)
- `research/x38/debate/018-search-space-expansion/final-resolution.md` (CLOSED)
- `research/x38/docs/v6_v7_spec_patterns.md`

---

## Preamble

I write as **architect / opening critic** per `AGENTS.md`. My role is to examine
the four findings in this topic — the architecture pillars, directory layout,
identity-axis model, and candidate-level vocabulary — for structural soundness,
completeness, and coherence with already-closed upstream decisions.

**Burden of proof** (rules.md §5): The current design (as stated in
`design_brief.md` and `findings-under-review.md`) stands unless I demonstrate it
is wrong or incomplete. Where I propose amendments, the burden is on me to show
why the current formulation is insufficient. Where I accept, I must still
identify the strongest counter-argument and address it.

**Critical upstream context**: Topic 007 (philosophy) is CLOSED — F-01 freezes
"inherit methodology, not answers" as invariant. Topic 002 (contamination
firewall) is CLOSED — 3 F-06 categories, state-machine enforcement, chmod as
secondary guardrail. Topic 001 (campaign model) is CLOSED — campaign defined by
required properties, container shape **deferred to architecture** (D-03). Topic
010 (clean OOS) is CLOSED — pre-existing candidate treatment Scenario 1
**deferred to Topic 008 F-13** (D-23). These closures constrain but do not
predetermine 008's decisions. Topic 017 (epistemic search policy) remains OPEN
and has a direct cross-topic tension with D-02 (pillar count).

This topic contains 4 findings with independent issue IDs. They are related —
architecture pillars, physical directory structure, identity versioning, and
candidate-level vocabulary — but each stands or falls on its own evidence. I
debate them as independent issues, not facets of a single finding.

---

## X38-D-02: Ba trụ cột kiến trúc — ACCEPT with amendment

### Position

The three-pillar architecture (Contamination Firewall, Protocol Engine,
Meta-Updater) is structurally sound and should be accepted as the v1 backbone.
Each pillar addresses a distinct enforcement concern with minimal overlap:

1. **Contamination Firewall** — *what* crosses campaign boundaries (Topic 002
   settled: 3 categories, state-machine hash-signing, typed schema).
2. **Protocol Engine** — *how* research proceeds within a campaign (8-stage
   pipeline, phase gating, freeze checkpoint).
3. **Meta-Updater** — *how methodology evolves* between campaigns (4 update
   types, F-01 invariant: never update priors about answers).

**Key argument**: The pillar decomposition follows separation of concerns along
the campaign lifecycle: pre-campaign (inherit knowledge → Firewall), intra-
campaign (execute research → Protocol Engine), post-campaign (distill lessons →
Meta-Updater). This is a natural factoring. Expert feedback (PLAN.md:664
[x38 internal]) named exactly these three. Topic 002 already validated pillar 1
through 6 rounds of adversarial debate. The remaining two are substantively
supported by `design_brief.md` §3.2–3.3 and the V6→V8 lineage evidence
[extra-archive: `x37/docs/gen1/RESEARCH_PROMPT_V6/`].

**However**: The open question — "cần trụ thứ 4?" — deserves rigorous analysis.
Three candidate 4th pillars have been raised:

**(a) Reproducibility Engine**: Deterministic pipeline execution (same input +
same code + same seed = same output) is a system-level property, not an
independent enforcement mechanism. It emerges from Protocol Engine's phase
gating (deterministic stage transitions) and Campaign model's data snapshots
(SHA-256 bound copies). A separate pillar would either duplicate Protocol Engine
responsibilities or create coordination overhead with no enforcement gain.
Per `online_vs_offline.md` §1 [x38 internal]: offline Alpha-Lab is
deterministic by construction — reproducibility is not an additional concern to
enforce but an inherent property of the paradigm.

**(b) Audit Trail Engine**: Audit is a cross-cutting capability, not a vertical
pillar. Every pillar produces auditable artifacts: Firewall produces
`contamination.json`, Protocol Engine produces stage artifacts, Meta-Updater
produces `lesson_history.json`. Promoting audit to a pillar either (i) extracts
artifact production from each pillar (breaking encapsulation) or (ii) adds a
redundant verification layer that can be implemented as a utility library without
architectural promotion. Evidence: `v6_v7_spec_patterns.md` [x38 internal]
Pattern 1 (Anomaly Disposition Register) shows audit as a *pattern within*
existing modules, not a separate pillar.

**(c) Epistemic Search Policy (ESP)**: Topic 017 (OPEN) proposes ESP as either a
sub-component or a promoted pillar (findings-under-review.md cross-topic tension
table [x38 internal]). ESP governs intra-campaign search illumination: descriptor
tagging, coverage maps, budget allocation, cell-elite archives. This is squarely
within Protocol Engine's domain — it is about *how the protocol searches*, not a
distinct enforcement boundary. The 8-stage pipeline (Stages 3–6 especially) is
the natural home for ESP substance. Promoting ESP to a 4th pillar would split
intra-campaign research governance into two pillars that must coordinate on the
same stage artifacts, violating the lifecycle factoring that makes the 3-pillar
model clean. If Protocol Engine becomes internally complex, the solution is
modular decomposition *within* the pillar (e.g., `protocol.search`,
`protocol.gating`, `protocol.validation`), not architectural promotion.

**Proposed amendment**: Accept the 3-pillar structure with an explicit
**responsibility mapping** that demonstrates completeness. The mapping should
list every v1 concern identified across closed topics and show which pillar
owns it. This prevents the "Protocol Engine as dumping ground" failure mode by
making assignments explicit and auditable. Concretely:

```
Pillar 1 (Firewall):
  - F-06 category validation (3 named categories — Topic 002)
  - State-machine hash-signing (D facet — Topic 002)
  - UNMAPPED + Tier 2 + SHADOW governance (E facet — Topic 002)
  - Filesystem chmod defense-in-depth (F facet — Topic 002)

Pillar 2 (Protocol Engine):
  - 8-stage pipeline execution + phase gating (design_brief §3.2)
  - Freeze checkpoint at Stage 7 (design_brief §3.2)
  - Benchmark embargo (RESEARCH_PROMPT_V6 line 284-292 [extra-archive])
  - Epistemic search: coverage map, cell-elite, budget governor (Topic 017)
  - Descriptor tagging and proof bundles (Topic 017/018)
  - Exhaustive scan over declared search space (online_vs_offline §1)

Pillar 3 (Meta-Updater):
  - 4 update types (design_brief §3.3)
  - F-01 invariant: never update priors about answers (Topic 007)
  - MK-17 shadow-only constraint on same-dataset (Topic 004)
  - Promotion ladder storage (Topic 017 ESP-03: v1 storage, v2 activation)
```

### Classification: Judgment call

Both sides (3 pillars vs 4) have defensible positions. The 3-pillar structure is
better supported by evidence, but the counter-argument (Protocol Engine overload)
is legitimate and cannot be dismissed by evidence alone. The question reduces to:
is the complexity of Protocol Engine's internal modularization lower than the
coordination cost of a 4th pillar? This is a judgment about future implementation
cost, not a provable fact.

---

## X38-D-09: Cấu trúc thư mục target — ACCEPT with amendments

### Position

The proposed directory structure (`findings-under-review.md` §F-09) correctly
implements the separation principle: Code ≠ Data ≠ Results ≠ Knowledge. The
`src/alpha_lab/` layout with 6 sub-packages mirrors the pillar architecture plus
the operational concerns (features, discovery, CLI). The principle of campaign
directory growth (`campaigns/` phình, rest stable) is sound and supported by the
Campaign model decisions (Topic 001 D-03: campaign defined by required
properties, container shape deferred to architecture).

**Key argument**: The structure answers Topic 001's deferred question — the
*container shape* of a campaign. Each `campaigns/cNNN_*/` directory is a
self-contained campaign artifact with `campaign.json`, `sessions/`, `convergence/`,
and `contamination.json`. This satisfies D-03's required properties: grouping
(directory boundary), protocol/dataset boundary (campaign.json references),
lineage (`inherits_from` field), and HANDOFF law (meta-knowledge output).
The `data/btcusdt/` directory with SHA-256 checksums ensures reproducibility
without symlink fragility (`design_brief.md` §6 [x38 internal]).

**However**, three gaps remain:

**(Gap 1) Missing `published/` directory**: x38 debate produces spec sections
that flow through `drafts/` → `published/` (PLAN.md §4.1 [x38 internal]). The
proposed directory structure omits where published specs live in the final
Alpha-Lab layout. If specs are co-located with code, they provide the
authoritative protocol definition that Protocol Engine executes. If outside,
there is a sync risk. The structure should include a `specs/` or `published/`
directory at root level for the frozen V1 protocol specification.

**(Gap 2) Campaign-level data binding**: The structure shows `data/btcusdt/` as a
shared data directory with checksums. But campaign.json references a data snapshot.
If two campaigns use different data ranges (C1: 2017–2026Q1, C2: 2017–2026Q3),
the data directory must support versioned snapshots. The current structure implies
a single data directory per asset, not per campaign. This needs clarification:
either (a) `data/` stores all historical snapshots and campaigns reference by
checksum, or (b) each campaign copies its data slice into `campaigns/cNNN/data/`.
Option (a) is more storage-efficient but requires immutability enforcement on the
shared data dir. Option (b) is fully self-contained per campaign but duplicates
data. This is a design choice the finding should make explicit.

**(Gap 3) No `monitoring/` or runtime directory**: While x38 is framework design
(not deployment — rules.md §19), the Campaign model includes "PENDING_CLEAN_OOS"
triggers and phase gating enforcement at runtime. These need a home. If they are
CLI concerns, `src/alpha_lab/cli/` suffices. But if the framework tracks
campaign states, governance obligations, and protocol versions across campaigns,
a `state/` or `runtime/` directory may be needed at root level for mutable
cross-campaign state (as distinct from immutable `campaigns/` artifacts and
evolving `knowledge/`).

**Proposed amendments**:

1. Add `specs/` at root level for published protocol specifications.
2. Clarify data binding model: recommend option (a) — shared `data/` directory
   with immutable snapshots referenced by checksum, plus a MANIFEST listing all
   available snapshots. Campaign.json references a specific checksum.
3. Address the three open questions from findings:
   - `knowledge/` at root: **Correct** — it is mutable state, not source code.
     Code reads knowledge, it does not contain it.
   - `data/` inside project: **Correct** — reproducibility requires co-located
     data with checksums. External data directories create a symlink-equivalent
     fragility risk.
   - `docs/` needed: **Minimal** — `CLAUDE.md` + `README.md` + `specs/` covers
     the documentation need. A separate `docs/` directory is unnecessary if specs
     have their own directory.

### Classification: Thiếu sót

The core structure is sound but incomplete. The gaps are omissions (not design
errors), and all three are addressable without restructuring.

---

## X38-D-13: Three-identity-axis model — ACCEPT with amendment

### Position

The three-identity-axis model from gen4 solves a paradigm-independent problem:
tracking which rules, which research program, and which candidate were in effect
for any given piece of evidence. This problem exists in both online and offline
paradigms (`online_vs_offline.md` §3 [x38 internal]: "Pattern paradigm-
independent — chẩn đoán → gaps → fixes"). Adopting the conceptual model is
correct; the implementation must be offline-native.

**Key argument**: Alpha-Lab already has 2 of the 3 axes:

| Gen4 axis | Alpha-Lab equivalent | Status |
|-----------|---------------------|--------|
| `program_lineage_id` | `campaign_id` | Exists (Topic 001 D-03) |
| `system_version_id` | Session-level frozen candidate | Exists (design_brief §4) |
| `constitution_version` | **Missing** | Gap identified by F-13 |

The missing axis (`protocol_version` in Alpha-Lab terms) creates a concrete
problem: Campaign C1 (protocol v1, 8 stages) and Campaign C3 (protocol v2, after
governance reform adds a 9th stage) produce results that are not directly
comparable. Without a protocol version tag, convergence analysis (Topic 013) would
compare apples and oranges. This is not hypothetical — the V4→V8 lineage
[extra-archive: `PLAN.md` §§1.1, design_brief §8] shows exactly this problem:
V6 introduced exhaustive scan (a protocol change), and V6 results cannot be
compared to V4 results at the same level of confidence.

**Evidence for all 3 axes being necessary** (not just 2):

1. `campaign_id` ≠ `protocol_version`: Multiple campaigns can use the same
   protocol version (e.g., C1 and C2 both use protocol v1 on different data).
   Multiple protocol versions can apply within the same research lineage.
   The axes are genuinely independent.
2. Topic 010 D-23 [x38 internal] explicitly deferred pre-existing candidate
   treatment "Scenario 1" to **Topic 008 F-13** — the identity schema. This
   confirms that 010 needs identity axes to be resolved before candidate
   treatment semantics are complete.
3. Topic 007 F-22 [x38 internal] froze 3 evidence types (coverage/process,
   deterministic convergence, clean adjudication). Each evidence type may have
   different validity across protocol versions. Protocol version tagging enables
   evidence-type validity tracking.

**However**: The finding proposes `protocol_version` without specifying change
triggers. When does the protocol version increment? The question matters because:
- Too frequent (every minor parameter change) → version inflation, most versions
  have ≤1 campaign, axis becomes uninformative.
- Too infrequent (only on major governance overhaul) → protocol changes within a
  version create invisible comparability gaps.

**Proposed amendment**: Accept all 3 axes. Define `protocol_version` change
triggers as:

1. **Major increment** (v1 → v2): When published spec changes affect stage
   definitions, gating criteria, or search space declaration format. Requires
   governance review (Meta-Updater cycle).
2. **Minor increment** (v1.0 → v1.1): When published spec changes affect default
   parameters, budget allocations, or proof bundle requirements without changing
   stage structure.
3. **No increment**: Bug fixes, documentation updates, tooling improvements that
   do not alter the research protocol's logical behavior.

`campaign.json` MUST declare `protocol_version` at creation time. Cross-campaign
convergence analysis MUST flag comparisons across major versions. Minor version
differences are flagged as warnings, not blocks.

### Classification: Thiếu sót

The gap (missing protocol_version axis) is genuine and evidenced. The fix
(add the axis + define change triggers) is additive, not restructuring.

---

## X38-SSE-04-IDV: Candidate-level identity vocabulary — SPLIT

### Position

This finding routes from Topic 018's 7-field breadth-activation contract
(`final-resolution.md:122-130` [x38 internal]). Field 3 (`identity_vocabulary`)
requires a deterministic structural pre-bucket: descriptor hash, parameter
family, AST-hash as subset. The correction note (`final-resolution.md:146-150`
[x38 internal]) correctly identifies that X38-D-13 covers protocol/campaign/
session identity axes — a **macro-identity** concern — while `identity_vocabulary`
is a **micro-identity** concern: when are two candidates structurally equivalent
for convergence and comparison purposes?

**Key argument**: These are two distinct abstraction levels that require different
expertise and different evidence:

| Aspect | D-13 (macro-identity) | SSE-04-IDV (micro-identity) |
|--------|----------------------|----------------------------|
| **Unit** | Campaign, session, protocol | Individual candidate |
| **Question** | "Which research context produced this?" | "Are these two candidates the same thing?" |
| **Enforcement** | Metadata tag in campaign.json | Structural hash + parameter family in scan artifacts |
| **Consumer** | Cross-campaign analysis, Meta-Updater | Convergence analysis, equivalence audit, surprise queue |
| **Evidence base** | V4→V8 lineage, gen4 constitution | V6/V7 spec patterns, Feature Library Schema |
| **Upstream** | Topic 007 (philosophy), Topic 001 (campaign) | Topic 017 (ESP-02 phenotype), Topic 018 (SSE-D-04) |

Merging micro-identity into D-13 would overload a finding that is already
well-scoped around the 3-axis model. Conversely, leaving it unowned creates a
gap in Topic 018's contract.

**However**: The question "008 or 013?" is not obvious. Topic 013 (convergence)
is the primary *consumer* of candidate equivalence — it needs to know when two
candidates are "the same" to perform convergence analysis. But Topic 017 (ESP)
also consumes it for equivalence audit and cell-elite maintenance (ESP-02
CandidatePhenotype contract). The vocabulary is a shared interface, not
exclusively owned by either consumer.

**Proposed resolution — SPLIT into interface + semantics**:

1. **Topic 008 scope (interface contract)**: Define that a `candidate_identity`
   schema MUST exist, specify its structural fields (descriptor hash, parameter
   family, AST-hash), and place it within the identity-axis framework as a 4th
   axis operating at a finer granularity than the other three. This is
   architecturally consistent: the identity model gains a candidate-level axis
   alongside protocol, campaign, and session axes. This satisfies Topic 018's
   field 3 routing obligation.

2. **Topic 013 scope (semantic rules)**: Define when two candidates are
   *equivalent* — the behavioral nearest-rival layer, threshold for "same
   parameter family," and implications for convergence counting. Topic 013 is
   the correct owner because equivalence semantics are convergence-specific.

3. **Topic 017 scope (consumption)**: Define how ESP consumes the vocabulary —
   CandidatePhenotype's reconstruction-risk gate, cell-elite deduplication,
   surprise queue admission. Topic 017 already owns ESP-02 which references this.

This split resolves Topic 018's routing obligation (field 3 owner = 008 for
interface, 013 for semantics, 017 for consumption) without overloading any
single topic.

**Concrete action for Topic 008**: Expand D-13 to a **four-axis identity model**:

```
protocol_version      ← which research rules
campaign_id           ← which research program
session_id            ← which frozen candidate instance
candidate_identity    ← which structural entity (descriptor hash + parameter family)
```

The first three axes are macro-level (campaign metadata). The fourth is
micro-level (scan artifact metadata). D-13 defines all four axes' structural
schema; downstream topics (013, 017) define semantic rules and consumption
patterns.

### Classification: Thiếu sót

The gap is real: Topic 018 identified a routing obligation that no current topic
owns completely. The proposed split is additive — it expands D-13's scope
without contradicting any closed decision.

---

## Summary

### Accepted (near-convergence candidates)

- **X38-D-02**: 3 pillars sufficient for v1. ESP folds into Protocol Engine.
  Audit and reproducibility are emergent properties. Amendment: explicit
  responsibility mapping.
- **X38-D-09**: Directory structure sound. Answers Topic 001's deferred container
  shape question. Amendments: add `specs/`, clarify data binding, resolve 3 open
  questions.
- **X38-D-13**: 3-axis model accepted, paradigm-independent. Amendment: define
  protocol_version change triggers (major/minor/none).

### Challenged (need debate)

- **X38-SSE-04-IDV**: Proposed SPLIT into 3 scopes (008 interface, 013
  semantics, 017 consumption). Counter-position that may emerge: keep
  candidate-level vocabulary entirely within 013. This needs debate because the
  routing decision affects Topic 018's closure integrity.

---

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 007 | F-01 | Philosophy must settle before pillars finalized | **RESOLVED**: 007 CLOSED, F-01 frozen. No remaining tension. |
| 017 | ESP-01→04 | ESP as sub-component (v1) vs pillar (v2). If 008 decides 3 sufficient, ESP folds into Protocol Engine | 008 owns pillar decision. Position stated: 3 pillars, ESP inside Protocol Engine. Awaiting 017 debate for substance. |
| 013 | (pending) | SSE-04-IDV scope split routes semantic rules to 013. If 013 rejects ownership, vocabulary falls back to 008 | 008 owns interface; 013 accepts or 008 absorbs. |
| 001 | D-03 | Campaign container shape deferred to architecture | **RESOLVED in this round**: D-09 proposes container shape. |
| 010 | D-23 | Pre-existing candidate treatment Scenario 1 deferred to 008 F-13 | D-13 + SSE-04-IDV together provide identity schema for 010's Scenario 1. |

---

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-D-02 | 3 pillars sufficient; ESP inside Protocol Engine | Judgment call | Open | Protocol Engine overload risk if ESP + 8 stages + budget → 4th pillar warranted | Overload is internal modularization problem, not architectural promotion signal — 4th pillar adds coordination cost without enforcement gain |
| X38-D-09 | Directory structure sound; 3 amendments proposed | Thiếu sót | Open | — | — |
| X38-D-13 | 3-axis model accepted; protocol_version change triggers defined | Thiếu sót | Open | — | — |
| X38-SSE-04-IDV | SPLIT: 008 owns interface, 013 owns semantics, 017 owns consumption | Thiếu sót | Open | — | — |
