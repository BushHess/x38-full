# Round 1 — Rebuttal: Architecture Pillars & Identity
**Topic**: 008 — Architecture Pillars & Identity
**Author**: codex
**Date**: 2026-03-26
**Responds to**: `claude_code/round-1_opening-critique.md`
**Scope**: X38-D-02 (Three pillars), X38-D-09 (Directory structure), X38-D-13 (Three-identity-axis model), X38-SSE-04-IDV (Candidate-level identity vocabulary)
**Artifacts read**:
- `AGENTS.md`
- `docs/online_vs_offline.md`
- `x38_RULES.md`
- `debate/rules.md`
- `debate/prompt_template.md`
- `debate/008-architecture-identity/README.md`
- `debate/008-architecture-identity/findings-under-review.md`
- `debate/008-architecture-identity/claude_code/round-1_opening-critique.md`
- `docs/design_brief.md`
- `PLAN.md`
- `docs/v6_v7_spec_patterns.md`
- `debate/001-campaign-model/final-resolution.md`
- `debate/002-contamination-firewall/final-resolution.md`
- `debate/007-philosophy-mission/final-resolution.md`
- `debate/010-clean-oos-certification/final-resolution.md`
- `debate/013-convergence-analysis/findings-under-review.md`
- `debate/015-artifact-versioning/findings-under-review.md`
- `debate/017-epistemic-search-policy/findings-under-review.md`
- `debate/018-search-space-expansion/final-resolution.md`
- `/var/www/trading-bots/btc-spot-dev/docs/research/RESEARCH_RULES.md` [extra-archive]
- `/var/www/trading-bots/btc-spot-dev/research/x37/README.md` [extra-archive]
- `/var/www/trading-bots/btc-spot-dev/research/x37/x37_RULES.md` [extra-archive]
- `/var/www/trading-bots/btc-spot-dev/research/x37/docs/gen1/RESEARCH_PROMPT_V6/PROMPT_FOR_V6_HANDOFF.md` [extra-archive]
- `/var/www/trading-bots/btc-spot-dev/research/x37/docs/gen4/core/research_constitution_v4.0.yaml` [extra-archive]

**Mandatory rule reminder**:
1. §4: Attack the argument, not the conclusion.
2. §7: Steel-man is required before marking `Converged`.
3. §8: No soft concession language; every concession must be evidence-backed.
4. §12: No new topic creation after round 1.

## Preamble

I keep the four issues separate, as required by the finding split already frozen in
`findings-under-review.md`. I also keep only claims that survive three checks:
wrong-target challenge, evidence-boundary check, and rules audit against
`debate/rules.md` §§4/7/8/11/12.

The main pattern in the opening critique is sound but uneven: several conclusions
are defensible, but some supporting mechanisms overreach the current authority
chain. Under §5, that matters. If the mechanism offered for changing or expanding
the design is not sourced, the current design does not become weak merely because
an alternative sounds plausible.

## X38-D-02 — Ba trụ cột kiến trúc

**Verdict**: accept the conclusion that v1 remains a three-pillar architecture;
reject the claim that pillar count still stands on equal footing with a four-pillar
alternative. Accept a responsibility map only as optional spec-hardening, not as
evidence that the architecture is still structurally undecided.

**Classification**: Judgment call

**Evidence pointers**:
- `docs/design_brief.md:34-90`
- `PLAN.md:663-669`
- `docs/online_vs_offline.md:25-35,44-54`
- `docs/v6_v7_spec_patterns.md:333-352`
- `debate/017-epistemic-search-policy/findings-under-review.md:350`

**Critique**:

The opening critique correctly defeats the three candidate "pillar 4" proposals,
but then keeps the pillar-count dispute artificially wide. The authority chain is
not neutral here. `design_brief.md:34-90` and `PLAN.md:663-669` positively source
three mandatory components. Topic 017 already records the explicit routing rule:
if Topic 008 keeps three pillars, ESP substance folds into Protocol Engine rather
than gaining architectural promotion
(`debate/017-epistemic-search-policy/findings-under-review.md:350`).

The rebuttal to "Reproducibility Engine" and "Audit Trail Engine" is largely right,
but its own evidence already narrows the dispute further than it admits.
`docs/online_vs_offline.md:25-35,47` treats reproducibility as an offline property
of deterministic execution, not a separate enforcement boundary. Likewise,
`docs/v6_v7_spec_patterns.md:333-352` identifies convergence reporting and
meta-knowledge extraction as subsystem gaps, not as proof that audit must become a
standalone pillar. Those are implementation obligations distributed across
Protocol Engine, artifact/version management, and Meta-Updater.

What survives as a real open question is much narrower: whether the spec should
freeze an explicit responsibility map so Protocol Engine does not become a vague
catch-all. That is a documentation/completeness question, not a still-live case
for a fourth pillar. If this issue remains `Open`, it should remain open on that
narrower basis.

## X38-D-09 — Cấu trúc thư mục target

**Verdict**: accept the checksum-bound data-reference clarification as the only
surviving completeness point. Reject the proposed `specs/`/`published/` gap as a
wrong-target argument, and reject the proposed `state/` or `runtime/` root as
unsupported topic creep.

**Classification**: Thiếu sót

**Evidence pointers**:
- `docs/design_brief.md:5,96-102,150-182`
- `PLAN.md:445-447,581-599,1038-1042`
- `x38_RULES.md:10-17,31-58,63-82`
- `debate/015-artifact-versioning/findings-under-review.md:90-110`
- `/var/www/trading-bots/btc-spot-dev/docs/research/RESEARCH_RULES.md:11,312` [extra-archive]

**Critique**:

Gap 1 attacks the wrong layer. `x38_RULES.md:10-17,31-58,63-82` and
`docs/design_brief.md:5` place `drafts/` and `published/` in the x38 design-study
workspace, where architecture decisions are debated and published. The alpha-lab
target tree in `docs/design_brief.md:150-167` and `PLAN.md:581-596` is the future
runtime repo layout. Importing x38's publication directories into alpha-lab is not
an omission in F-09; it is a category error between blueprint-governance and the
system being specified.

Gap 2 is directionally useful but overstated. The current record already says
campaigns bind to a fixed dataset snapshot with SHA-256 and already shows
`campaign.json` carrying a data reference (`docs/design_brief.md:96-102,179-182`,
`PLAN.md:445-447,592-594`). So the surviving amendment is narrower than the
opening critique claims: make the immutable snapshot identifier or checksum field
explicit in `campaign.json`. That is clarification of the existing model, not proof
that the model is undecided between shared snapshots and per-campaign copies.

Gap 3 is not source-backed in this topic. `PLAN.md:1038-1042` shows state-tracking
form is still an execution-design question, and `debate/015-artifact-versioning/findings-under-review.md:90-110`
shows version/invalidation metadata is already a separate open topic. Freezing a
top-level `state/` or `runtime/` directory here would preempt unresolved Topic 003
and 015 work without evidence that a root mutable-store is architecturally
necessary.

On the remaining battlegrounds: `knowledge/` at root is already the cleaner read of
the record because `PLAN.md:598-599` and `docs/design_brief.md:163-166` separate
code, data, results, and knowledge. `data/` inside the project is likewise sourced
by the anti-symlink reproducibility argument in `docs/design_brief.md:179-182`.
By contrast, venv topology is not well supported as an architectural invariant: the
current research repo uses a shared venv
(`/var/www/trading-bots/btc-spot-dev/docs/research/RESEARCH_RULES.md:11,312`
[extra-archive]), while the proposed alpha-lab tree lives outside that repo. That
makes venv choice packaging/operations policy, not a backbone directory decision.

## X38-D-13 — Three-identity-axis model

**Verdict**: accept the missing protocol-version axis; reject the attempt to freeze
major/minor/no-increment trigger law inside Topic 008. Topic 008 owns the schema
surface. Topic 003 and Topic 015 still own too much of the underlying change
semantics for 008 to close that taxonomy cleanly.

**Classification**: Thiếu sót

**Evidence pointers**:
- `docs/design_brief.md:96-102`
- `debate/001-campaign-model/final-resolution.md:110-123,166-175,183-200`
- `debate/010-clean-oos-certification/final-resolution.md:120-123,152-156,176`
- `debate/015-artifact-versioning/findings-under-review.md:92-110`
- `docs/online_vs_offline.md:58-94`
- `/var/www/trading-bots/btc-spot-dev/research/x37/docs/gen4/core/research_constitution_v4.0.yaml:23-67` [extra-archive]

**Critique**:

The opening critique is right on the core omission: Alpha-Lab needs an explicit
protocol-identity axis in addition to campaign/session provenance. Topic 001
already froze the consumption-side invariant
`protocol_identity_change -> new campaign boundary` and explicitly deferred the
identity/version schema to Topic 008
(`debate/001-campaign-model/final-resolution.md:110-123,166-175,183-200`). Topic
010 likewise deferred Scenario 1's same-family comparison contract to Topic 008
(`debate/010-clean-oos-certification/final-resolution.md:120-123,152-156,176`).
So the missing-axis diagnosis survives review.

What does not survive review is the proposed change-trigger taxonomy. Topic 001
deferred the schema to 008, but it did not give 008 unilateral ownership of what
counts as a protocol-semantic change. Topic 003 still owns protocol content, and
Topic 015 is still debating which kinds of engine, feature, metric, or protocol
changes alter trade logs, rankings, verdicts, and invalidation scope
(`debate/015-artifact-versioning/findings-under-review.md:92-110`). Until those
topics close, a major/minor/no-change matrix in 008 would be naming outcomes whose
semantic tests are not frozen yet.

The opening critique also understates tension with Topic 001's burden-of-proof
default. `debate/001-campaign-model/final-resolution.md:121-123,139-143` says that
if protocol-identity preservation is unproven, routing defaults to HANDOFF rather
than permissive same-protocol treatment. A "minor version = warning only" rule is
therefore premature. It risks downgrading identity disputes that 001 currently
tells us to treat conservatively.

Gen4 remains useful evidence for the existence of separated axes
(`/var/www/trading-bots/btc-spot-dev/research/x37/docs/gen4/core/research_constitution_v4.0.yaml:23-67`
[extra-archive]), but `docs/online_vs_offline.md:58-94` blocks direct import of
online redesign/versioning machinery as an offline template. The evidence-backed
v1 move is narrower: add the protocol-version axis and required metadata surface;
defer precise bump semantics until Topics 003 and 015 define what materially
changes protocol identity.

## X38-SSE-04-IDV — Candidate-level identity vocabulary

**Verdict**: accept that candidate-level identity vocabulary is a real unresolved
routing obligation and cannot be silently left ownerless. Reject the proposed fix
of absorbing it into D-13 as a fourth identity axis. Also reject the framing that
017 is merely a downstream consumer.

**Classification**: Thiếu sót

**Evidence pointers**:
- `debate/018-search-space-expansion/final-resolution.md:122-130,146-150,188-210,301-314,329`
- `debate/013-convergence-analysis/findings-under-review.md:209-225`
- `debate/017-epistemic-search-policy/findings-under-review.md:114-118,148-153`

**Critique**:

The opening critique is correct that Topic 018 left a real routing gap.
`debate/018-search-space-expansion/final-resolution.md:122-130` freezes the
7-field breadth-activation interface and marks field 3 (`identity_vocabulary`) as
unresolved. The correction note at `:146-150` is explicit: current 008 scope per
X38-D-13 covers protocol/campaign/session identity axes, while candidate-level
equivalence vocabulary remains TBD. That gap is real and belongs in this topic.

But the proposed cure overreaches the source text. Expanding D-13 into a
four-axis model collapses two findings that the topic file already split:
macro-level provenance axes (D-13) and candidate-level equivalence vocabulary
(X38-SSE-04-IDV). Topic 018 does not say "add a fourth axis"; it says owner
assignment is unresolved and may require 008 scope expansion
(`debate/018-search-space-expansion/final-resolution.md:301-314,329`).

The ownership split is also more granular than the opening critique admits. Topic
013 already owns the operational equivalence questions: behavioral thresholds and
structural hash granularity for pre-bucketing
(`debate/013-convergence-analysis/findings-under-review.md:209-225`). Topic 017 is
not only a consumer; it already owns descriptor-rich phenotype contracts
(`debate/017-epistemic-search-policy/findings-under-review.md:114-118,148-153`),
and Topic 018 routes `descriptor_core_v1` to 017 before field 3 can be fully
useful. So the real downstream split is:

- 008: architectural placement and contract existence for candidate-level identity
- 017: descriptor primitives that feed the structural pre-bucket
- 013: equivalence semantics, thresholds, and structural-hash granularity

That preserves the four-issue separation requested in this topic. It also avoids
quietly enlarging D-13 until it swallows SSE-04-IDV. If 008 exports anything in
v1 here, it should export the requirement that a candidate-level identity
vocabulary object must exist and remain distinct from protocol/campaign/session
axes, not a premature four-axis ontology.

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-D-02 | Keep 3 pillars; no evidence-backed 4th pillar. Only narrower responsibility-mapping question survives | Judgment call | Open | — | — |
| X38-D-09 | Accept checksum-binding clarification; reject `published/` and `state/` as architecture gaps | Thiếu sót | Open | — | — |
| X38-D-13 | Add protocol-version axis; do not freeze bump taxonomy before 003/015 close | Thiếu sót | Open | — | — |
| X38-SSE-04-IDV | Keep candidate vocabulary as separate finding; do not absorb it into D-13 as axis 4 | Thiếu sót | Open | — | — |
