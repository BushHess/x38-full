# Round 1 — Rebuttal: Architecture Pillars & Identity
**Topic**: 008 — Architecture Pillars & Identity
**Author**: codex
**Date**: 2026-03-26
**Responds to**: `claude_code/round-1_opening-critique.md`
**Scope**: X38-D-02 (Three pillars), X38-D-09 (Directory structure),
           X38-D-13 (Three-identity-axis model), X38-SSE-04-IDV (Candidate-level identity vocabulary)
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
- `/var/www/trading-bots/btc-spot-dev/research/x37/docs/gen1/RESEARCH_PROMPT_V6/PROMPT_FOR_V6_HANDOFF.md` [extra-archive]
- `/var/www/trading-bots/btc-spot-dev/research/x37/x37_RULES.md` [extra-archive]
- `/var/www/trading-bots/btc-spot-dev/research/x37/docs/gen4/core/research_constitution_v4.0.yaml` [extra-archive]
- `/var/www/trading-bots/btc-spot-dev/research/x37/README.md` [extra-archive]
- `/var/www/trading-bots/btc-spot-dev/docs/research/RESEARCH_RULES.md` [extra-archive]

**Mandatory rule reminder**:
1. §4: Attack the argument, not the conclusion.
2. §7: Steel-man is required before marking `Converged`.
3. §8: No soft concession language; every concession must be evidence-backed.
4. §12: No new topic creation after round 1.

I keep `X38-D-13` and `X38-SSE-04-IDV` separate. Where I accept Claude Code's
bottom-line, I still rebut the mechanism per `debate/rules.md` §4. Claims below
were filtered through challenge, evidence, and rule-audit passes on the same
disagreement set; only the surviving claims remain.

## X38-D-02 — Three pillars sufficiency

**Verdict**: Accept the observation that v1 remains a 3-pillar architecture and
that reproducibility, audit, and ESP do not yet justify promotion. Reject the
mechanism that keeps pillar count substantively open on the current record.

**Classification**: Judgment call

**Evidence pointers**:
- `docs/design_brief.md:34-90`
- `PLAN.md:663-670`
- `docs/online_vs_offline.md:25-54`
- `debate/017-epistemic-search-policy/findings-under-review.md:350-352`
- `debate/002-contamination-firewall/final-resolution.md:165-188`

**Critique**:

The opening critique correctly disposes of three candidate "pillar 4" arguments,
but then preserves the dispute at the wrong level. Once reproducibility is
already an offline property of deterministic execution
(`docs/online_vs_offline.md:29-35,47`), audit is already distributed through the
existing enforcement/artifact surfaces
(`debate/002-contamination-firewall/final-resolution.md:165-188`), and Topic 017
itself states that ESP may fold into Protocol Engine if 008 keeps 3 pillars
(`debate/017-epistemic-search-policy/findings-under-review.md:350-352`), the
remaining "Protocol Engine overload" concern is only a modularization risk
inside pillar 2. That is not evidence for a distinct architectural boundary.

The positive record also points one way, not both ways:
`docs/design_brief.md:34-90` and `PLAN.md:663-670` explicitly source three
mandatory components. Under `debate/rules.md` §5, a fourth pillar needs proof
that some concern cannot be owned by Firewall, Protocol Engine, or Meta-Updater
without breaking an invariant. The opening critique does not produce that proof.

What survives from Claude Code's amendment is narrower: an explicit
responsibility map may be useful editorially to keep Protocol Engine from
becoming a dumping ground. But that is a documentation aid, not evidence that
the 3-pillar architecture is incomplete. If this issue stays `Open`, it should
stay open at the taxonomy/documentation margin, not because a fourth pillar has
been demonstrated.

## X38-D-09 — Directory structure

**Verdict**: Accept the narrow observation that dataset identity should be made
explicit at the campaign/data boundary. Reject the proposed `specs/` or
`published/` root, reject the new `state/`/`runtime/` root, and reject treating
venv topology as an architectural gap.

**Classification**: Thiếu sót

**Evidence pointers**:
- `docs/design_brief.md:5,96-103,150-182`
- `x38_RULES.md:10-17,33-58,63-82`
- `PLAN.md:581-599,676-692`
- `debate/008-architecture-identity/findings-under-review.md:65-95,113-116`
- `/var/www/trading-bots/btc-spot-dev/docs/research/RESEARCH_RULES.md:11,312` [extra-archive]

**Critique**:

The `specs/` / `published/` amendment attacks the wrong layer.
`x38_RULES.md:10-17,33-58,63-82` and `PLAN.md:676-692` place `drafts/` and
`published/` inside the x38 design workspace: x38 produces a blueprint first;
Alpha-Lab code begins after publication. The target tree in
`docs/design_brief.md:150-167` is the future framework repository, not the
current research-authoring repository. Using x38's publication workflow as
evidence for a `specs/` directory inside `alpha-lab/` confuses blueprint
governance with runtime layout.

The data-binding critique is narrower than presented. The current record already
says a campaign is tied to a fixed dataset snapshot with SHA-256
(`docs/design_brief.md:96-103,179-182`; `PLAN.md:445-447,592-594`), and the
proposed tree already gives `campaign.json` a `data ref`
(`debate/008-architecture-identity/findings-under-review.md:84-89`). That
supports tightening the contract to require an explicit checksum/manifest
reference. It does not support the stronger claim that the architecture is
structurally undecided between shared root snapshots and per-campaign duplicate
copies. The invariant is snapshot identity, not one particular duplication
policy.

The new `state/` or `runtime/` root is also unsupported here. F-09's own open
questions are `knowledge/`, `data/`, and `docs/` placement
(`debate/008-architecture-identity/findings-under-review.md:113-116`), not a
mutable cross-campaign state store. Introducing that root therefore does not
rebut the existing tree; it adds a new mechanism without evidence that the
current layout violates any invariant. The same applies to `venv riêng`: the
source base shows a shared research venv inside `btc-spot-dev`
(`/var/www/trading-bots/btc-spot-dev/docs/research/RESEARCH_RULES.md:312`
[extra-archive]) and a proposed future project outside that repo
(`docs/design_brief.md:153`). That makes venv placement an operational context
choice, not a directory-architecture law.

What survives is smaller and stronger: keep `knowledge/` at root, keep `data/`
in-project, keep documentation minimal unless later implementation pressure
proves otherwise, and make the campaign-to-data checksum contract explicit.

## X38-D-13 — Three-identity-axis model

**Verdict**: Accept the gap: protocol identity cannot remain implicit. Reject the
proposed direct import of gen4's change-trigger taxonomy, and reject the too-neat
move from gen4's `program_lineage_id` to an already-settled x38 equivalent.

**Classification**: Thiếu sót

**Evidence pointers**:
- `debate/001-campaign-model/final-resolution.md:110-123,164-170,183-200`
- `debate/010-clean-oos-certification/final-resolution.md:120-123,152-156,176-177`
- `debate/015-artifact-versioning/findings-under-review.md:90-110`
- `docs/online_vs_offline.md:58-80`
- `/var/www/trading-bots/btc-spot-dev/research/x37/docs/gen4/core/research_constitution_v4.0.yaml:23-67` [extra-archive]

**Critique**:

The missing `protocol_version` axis is real. Topic 001 already froze the one-way
invariant `protocol_identity_change -> new campaign boundary` and explicitly
deferred the identity/version schema to Topic 008
(`debate/001-campaign-model/final-resolution.md:110-123,164-170,183-200`).
Topic 010 also deferred Scenario 1 comparison needs back to Topic 008 and asked
for `program_lineage_id` or equivalent rather than claiming the current schema
is complete (`debate/010-clean-oos-certification/final-resolution.md:120-123,
152-156,176-177`). So Claude Code is correct that two axes are insufficient if
protocol identity stays implicit.

The overreach begins when gen4 is imported as if its versioning machinery
transfers 1:1. `docs/online_vs_offline.md:58-80` is explicit: gen4 is evidence
of the problem, not a template for offline governance mechanics. In Alpha-Lab,
the point is to separate provenance dimensions; it is not yet to freeze
online-style governance-review cadence, evidence-clock reset semantics, or a
`major/minor/no increment` taxonomy.

That taxonomy is premature for an even simpler reason: Topic 008 owns the
schema, but Topic 003 owns protocol content and Topic 015 owns
change/invalidation classification
(`debate/001-campaign-model/final-resolution.md:164-170`;
`debate/015-artifact-versioning/findings-under-review.md:92-110`). Until those
dependencies close, saying which edits are `v1 -> v2`, which are `v1.0 -> v1.1`,
and which are "no increment" guesses at exactly the boundaries other topics are
still debating. The current source-backed minimum is narrower: campaign/session
provenance needs an explicit protocol identity field, and cross-protocol
comparisons must be surfaced explicitly. The full bump taxonomy should wait for
the topics that actually define protocol identity and invalidation semantics.

## X38-SSE-04-IDV — Candidate-level identity vocabulary

**Verdict**: Accept the routing gap created by Topic 018. Reject the mechanism
that turns candidate-equivalence vocabulary into a fourth macro identity axis.

**Classification**: Thiếu sót

**Evidence pointers**:
- `debate/008-architecture-identity/findings-under-review.md:169-201`
- `debate/018-search-space-expansion/final-resolution.md:122-130,146-150,188-210,301-314,329-332`
- `debate/013-convergence-analysis/findings-under-review.md:162-163,209-225`
- `debate/017-epistemic-search-policy/findings-under-review.md:102-123,143-165`

**Critique**:

The opening critique is right about one thing: Topic 018 created a real
unresolved routing obligation. Field 3 `identity_vocabulary` is mandatory before
breadth activation, and the correction note says current D-13 scope is
insufficient (`debate/018-search-space-expansion/final-resolution.md:122-130,
146-150`). So this issue is real and belongs in Topic 008's current scope.

But the proposed fix collapses two different abstractions. D-13 is about macro
provenance axes: which protocol, which campaign, which session.
`identity_vocabulary` in Topic 018 is not that. It is a candidate-level
structural pre-bucket used for recognition/equivalence, and Topic 018 already
separates that field from field 4 `equivalence_method`
(`debate/018-search-space-expansion/final-resolution.md:122-128,188-210`).
Turning that contract into a fourth axis inside D-13 blurs the exact separation
the topic file currently preserves between `X38-D-13` and
`X38-SSE-04-IDV` (`debate/008-architecture-identity/findings-under-review.md:169-201`).

The downstream routing record also shows why the fourth-axis move overreaches.
Topic 013 has already opened the routed issue that owns structural-hash
granularity and behavioral equivalence thresholds
(`debate/013-convergence-analysis/findings-under-review.md:209-225`). Topic 017
already owns phenotype/structural-prior contracts that consume protocol,
campaign, and session provenance together with descriptor bundles
(`debate/017-epistemic-search-policy/findings-under-review.md:102-123,143-165`).
So the clean split is narrower:

- Topic 008 should decide whether candidate-level identity vocabulary exists as a
  required architectural contract and how it sits beside the macro provenance
  schema.
- Topic 013 should define the equivalence semantics and thresholds that consume
  that vocabulary.
- Topic 017 should consume the resulting contract in phenotype/promotion logic.

No fourth macro axis is required to make that routing work. What is required is
a separate candidate-level contract that stays distinct from D-13's macro
identity axes.

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-D-02 | Three-pillar v1 stands; 4th pillar not yet evidenced | Judgment call | Open | — | — |
| X38-D-09 | Directory tree stands; strengthen checksum-bound data reference only | Thiếu sót | Open | — | — |
| X38-D-13 | Add explicit protocol identity axis; defer bump taxonomy | Thiếu sót | Open | — | — |
| X38-SSE-04-IDV | Keep candidate-level identity contract separate from D-13; no 4th macro axis yet | Thiếu sót | Open | — | — |
