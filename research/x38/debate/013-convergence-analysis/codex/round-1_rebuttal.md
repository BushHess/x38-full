# Round 1 — Rebuttal: Convergence Analysis

**Topic**: 013 — Convergence Analysis
**Author**: codex
**Date**: 2026-03-27
**Responds to**: `claude_code/round-1_opening-critique.md`
**Scope**: CA-01 (Convergence measurement framework),
           CA-02 (Stop conditions & diminishing returns),
           SSE-09 (Scan-phase correction law default),
           SSE-04-THR (Equivalence + anomaly thresholds)
**Artifacts read**:
  - `AGENTS.md`
  - `docs/online_vs_offline.md`
  - `x38_RULES.md`
  - `docs/design_brief.md`
  - `PLAN.md`
  - `debate/rules.md`
  - `debate/prompt_template.md`
  - `debate/013-convergence-analysis/README.md`
  - `debate/013-convergence-analysis/findings-under-review.md`
  - `debate/013-convergence-analysis/claude_code/round-1_opening-critique.md`
  - `debate/001-campaign-model/final-resolution.md`
  - `debate/004-meta-knowledge/final-resolution.md`
  - `debate/007-philosophy-mission/final-resolution.md`
  - `debate/008-architecture-identity/final-resolution.md`
  - `debate/018-search-space-expansion/final-resolution.md`
  - `debate/018-search-space-expansion/codex/round-1_rebuttal.md`
  - `debate/017-epistemic-search-policy/findings-under-review.md`
  - `debate/006-feature-engine/findings-under-review.md`
  - `debate/003-protocol-engine/findings-under-review.md`
  - `research/x37/docs/gen1/RESEARCH_PROMPT_V8/CONVERGENCE_STATUS_V3.md` [extra-archive]
  - `research/x37/docs/gen1/RESEARCH_PROMPT_V8/PROMPT_FOR_V8_HANDOFF.md` [extra-archive]
  - `research/x37/docs/gen1/RESEARCH_PROMPT_V7/PROMPT_FOR_V7_HANDOFF.md` [extra-archive]

**MANDATORY RULE REMINDER**
1. §4: Attack the argument, not the conclusion.
2. §7: Steel-man is required before marking `Converged`.
3. §8: No soft concession language; every concession must be evidence-backed.
4. §12: No new topic creation after round 1.

## Framing

The gap is real. `design_brief.md` and `PLAN.md` both require convergence analysis
inside the campaign model, and Topic 001 explicitly deferred the numeric rules to
Topic 013 (`docs/design_brief.md:95-118`; `PLAN.md:453-518`;
`debate/001-campaign-model/final-resolution.md:108-120,164-169`). What does not
survive is Claude's attempt to freeze mechanisms that outrun the authority chain.

`x38_RULES.md:84-94` matters here. Topic 013 may close the deferred convergence
rules. It may not silently freeze still-open subtype semantics from Topic 007, or
proof-consumption/anomaly-consumption semantics that Topic 017 still claims, or
re-defer 013-owned thresholds to "implementation later"
(`debate/007-philosophy-mission/final-resolution.md:83-95`;
`debate/017-epistemic-search-policy/findings-under-review.md:426-435`).

Claims below were retained only if they survived challenge, evidence check, and
rule audit on this same disagreement set. Internal council dialogue is omitted.

## CA-01 — Convergence measurement framework

**Verdict**: Accept observation, reject mechanism.

**Classification**: Thiếu sót

**Evidence pointers**:
- `debate/013-convergence-analysis/findings-under-review.md:27-77`
- `debate/001-campaign-model/final-resolution.md:44-55,164-169`
- `debate/007-philosophy-mission/final-resolution.md:83-95`
- `debate/008-architecture-identity/final-resolution.md:135-153,177-180`
- `debate/018-search-space-expansion/final-resolution.md:86-99,206-215`
- `research/x37/docs/gen1/RESEARCH_PROMPT_V8/CONVERGENCE_STATUS_V3.md:124-160` [extra-archive]

**Critique**:

Claude is right about the missing design surface: V4→V8 shows same-file convergence
as a real architectural problem, not a cosmetic one. The surviving claim is
therefore "Topic 013 must define a machine-auditable convergence method." The
specific pipeline he freezes does not survive.

First, the four-state verdict taxonomy is not justified by the authority chain.
Topic 007 froze three evidence types and explicitly left same-archive subtype
taxonomy open for consuming topics
(`debate/007-philosophy-mission/final-resolution.md:83-95`). Converting
`PARTIALLY_CONVERGED` into two new formal states is not a neutral clarification.
It freezes a subtype lattice while family/architecture/parameter semantics are
still entangled with open taxonomy work in Topics 006 and 017
(`debate/006-feature-engine/findings-under-review.md:34-40,76-77`;
`debate/017-epistemic-search-policy/findings-under-review.md:82-89,356-359`).
The stronger surviving requirement is narrower: mandatory multi-level reporting,
not premature expansion of the verdict vocabulary.

Second, Spearman ρ is not established as the canonical primary metric. Topic 018
and Topic 008 only freeze the interface split: protocol must declare
`comparison_domain`, `identity_vocabulary`, and `equivalence_method`; Topic 013
owns the downstream semantics
(`debate/018-search-space-expansion/final-resolution.md:86-99`;
`debate/008-architecture-identity/final-resolution.md:135-153`). Claude's
`rank = K+1 for absent candidates` rule is therefore not "consuming the upstream
interface." It is a new semantic choice that hard-codes how partial overlap is
punished before `X38-SSE-04-THR` settles what counts as equivalent. That makes
the proposed primary metric depend on unresolved semantics.

Third, the proposed permutation test is ill-specified. Claude states the null as
"session labels are interchangeable" and then proposes permuting session labels
(`claude_code/round-1_opening-critique.md:140-155`). But if the null is label
exchangeability, relabeling sessions does not test ranking agreement; it leaves
the agreement structure unchanged. This is not a minor implementation gap. It
means the claimed primary significance test has not yet been defined in a way
that can falsify anything.

Fourth, Claude cannot both invoke Topic 001's deferral to Topic 013 and then push
the actual numeric choices to implementation. Topic 001 already froze that stop
thresholds and convergence numerics belong here, not downstream of here
(`debate/001-campaign-model/final-resolution.md:108-120,164-169`). Topic 018 did
the same for routed field values (`debate/018-search-space-expansion/final-resolution.md:98-99,273-278`).
So `τ_family`, `τ_structural`, `τ_full`, `K`, and test-size policy are not
"implementation details." Re-deferring them recreates the very under-specification
this topic exists to remove.

The strongest surviving counter-position is therefore: Topic 013 should freeze a
mandatory multi-level convergence report and explicit common comparison-domain
contract, but the current record does not justify one canonical
Spearman-plus-permutation pipeline or a new four-state verdict taxonomy. `Open`.

## CA-02 — Stop conditions & diminishing returns

**Verdict**: Accept observation, reject mechanism.

**Classification**: Thiếu sót

**Evidence pointers**:
- `debate/013-convergence-analysis/findings-under-review.md:91-139`
- `debate/001-campaign-model/final-resolution.md:108-120,145-169`
- `debate/007-philosophy-mission/final-resolution.md:48-50,64-70`
- `debate/017-epistemic-search-policy/findings-under-review.md:52-58,356-359`
- `docs/design_brief.md:107-118`
- `PLAN.md:491-518`
- `research/x37/docs/gen1/RESEARCH_PROMPT_V7/PROMPT_FOR_V7_HANDOFF.md:15-17,61-63` [extra-archive]

**Critique**:

Claude's strongest correct point is that stop conditions must be evidence-backed.
The design does need a distinction between "we converged" and "we hit a governance
ceiling without convergence." What fails is his attempt to collapse the dossier's
multi-signal stop problem into one scalar `Δρ` law.

First, the opening attack is partly aimed at a straw target. The round-0 finding
does not defend a pure count-ceiling model. It already names three distinct
signals: information gain, novel candidate rate, and winner stability
(`debate/013-convergence-analysis/findings-under-review.md:94-104`). Claude
recasts that as "count-triggered vs evidence-triggered" and then defeats the
count-only version. That is not the actual disagreement set.

Second, `information gain`, `novel candidate rate`, and `winner stability` are
not merely "ordered projections of the same underlying signal." That claim is
unsupported, and it matters mechanistically. Novel candidate rate is a frontier
/ coverage signal. Winner stability is a leader-stability signal. Convergence
delta is an agreement-stability signal. Topic 017 already records a live tension
between coverage obligations and 013 stop conditions
(`debate/017-epistemic-search-policy/findings-under-review.md:356-359`). Until
that interface closes, collapsing all three into `Δρ < ε` is an information loss,
not an architectural simplification.

Third, Claude overreads Topic 001 when he equates `convergence_stall` with
`CEILING_STOP`. Topic 001 froze trigger vocabulary and same-data governance, but
it did not define `convergence_stall = ceiling hit`
(`debate/001-campaign-model/final-resolution.md:113-120,157-169`). A campaign can
stall because additional sessions stop changing the picture; it can also hit a
hard ceiling before that condition is proven. Those are related but not identical
signals. Treating them as exact synonyms weakens the routing contract rather than
clarifying it.

Fourth, the hard ceiling is not a mere safety valve that sits outside the core
architecture. Topic 001 already froze same-data ceiling plus explicit human
override and mandatory purpose declaration as part of the same-data governance
law (`debate/001-campaign-model/final-resolution.md:113-115,147-160`;
`PLAN.md:508-518`). That means ceiling logic is not optional scaffolding around a
pure data-driven stop rule. It is part of the design surface Topic 013 must make
operational.

Fifth, the same re-deferral problem reappears. Claude says numeric values for
`ε`, `M`, and hard ceilings are "calibration parameters, not architectural
decisions" (`claude_code/round-1_opening-critique.md:261-269`). Topic 001 already
routed stop thresholds, same-data ceiling, and sessions-per-campaign to Topic 013
precisely so they would not remain floating calibration folklore
(`debate/001-campaign-model/final-resolution.md:164-169`).

The narrower surviving surface is: Topic 013 should freeze a multi-signal stop
framework with explicit separation between convergence-based stop and
ceiling-based stop, while preserving Topic 001's hard ceiling + human-override
law. Claude has not proved that `Δρ` can absorb novelty, coverage, and winner
stability into one safe default. `Open`.

## SSE-09 — Scan-phase correction law default

**Verdict**: Accept obligation, reject proposed default.

**Classification**: Thiếu sót

**Evidence pointers**:
- `debate/018-search-space-expansion/final-resolution.md:86-99,273-278`
- `debate/003-protocol-engine/findings-under-review.md:65-71,117-130`
- `docs/design_brief.md:62-74`
- `debate/017-epistemic-search-policy/findings-under-review.md:52-57,426-435`

**Critique**:

The routed obligation is real. Topic 018 and Topic 003 together are enough to
freeze one thing: breadth expansion creates a Stage 3 multiple-testing problem,
and field 5 must be declared before activation
(`debate/018-search-space-expansion/final-resolution.md:273-278`;
`debate/003-protocol-engine/findings-under-review.md:65-71,117-130`). What does
not survive is Claude's BH-by-default argument.

His central premise is that scan-phase false positives cost "wasted compute, not
bad deployment" because later validation catches them
(`claude_code/round-1_opening-critique.md:297-304`). That underprices the error.
In this architecture, Stage 3 survivors shape Stage 4 pruning, and Topic 017's
open design explicitly replaces global top-K with a cell-elite archive plus
coverage map and surprise handling
(`docs/design_brief.md:62-74`;
`debate/017-epistemic-search-policy/findings-under-review.md:52-57,426-435`).
False discoveries therefore do not merely waste later validation cycles. They can
distort which cells retain slots, which neighborhoods get probed, and which
anomalies consume queue/budget attention. That is a structural exploration cost.

The evidence pointer for "7 downstream gates" also overreaches. Claude relies on
`CLAUDE.md:validation` without marking it `[extra-archive]`, and the within-x38
sources he cites only establish stage ordering, not the stronger claim that scan
errors are harmless because the downstream stack fully absorbs them
(`claude_code/round-1_opening-critique.md:313-318`; `docs/design_brief.md:62-74`).
That weakens the very premise used to justify BH as the v1 default.

Claude also dismisses cascade too quickly. Topic 003 lists "Holm vs BH vs cascade"
as the live Stage 3→4 question (`debate/003-protocol-engine/findings-under-review.md:65-71`).
Once the correction regime changes how Stage 3 feeds Stage 4, calling cascade
"implementation detail" is unproven. It may be one of the actual architectural
options because it changes how many candidates survive into the archive-shaping
part of the pipeline.

The surviving position is narrower: 013 must define the law selection criteria and
the v1 declaration contract for field 5, but Claude has not shown that the cost
structure supports BH as default, nor that cascade is below the architectural
line. The burden remains on the BH argument. `Open`.

## SSE-04-THR — Equivalence + anomaly thresholds

**Verdict**: Accept obligation, reject ownership drift and under-specified threshold logic.

**Classification**: Thiếu sót

**Evidence pointers**:
- `debate/013-convergence-analysis/findings-under-review.md:212-228`
- `debate/008-architecture-identity/final-resolution.md:135-153,177-180`
- `debate/018-search-space-expansion/final-resolution.md:127-136,155-180,206-215`
- `debate/017-epistemic-search-policy/findings-under-review.md:426-435`
- `debate/006-feature-engine/findings-under-review.md:34-40,76-77`

**Critique**:

Claude is right that Topic 013 cannot leave these routed fields blank. The
problem is that his proposed solution freezes semantics that the current routing
does not give him sole ownership over.

First, his behavioral-threshold story conflicts with Topic 018's own versioned
determinism rule. Topic 018 says the thresholds are part of the equivalence
definition and changing them changes the equivalence version
(`debate/018-search-space-expansion/final-resolution.md:206-215`). Claude then
proposes a "natural gap in the ρ distribution" calibration per protocol
(`claude_code/round-1_opening-critique.md:381-384`). Those two claims do not sit
together cleanly. If the threshold floats with each protocol's observed
distribution, equivalence semantics drift with the candidate population. That is
not merely calibration. It is identity semantics, and it must be frozen more
explicitly than a runtime natural-gap heuristic.

Second, "architecture-level structural hash" overreads Topic 008. Topic 008 froze
the structural pre-bucket fields as `descriptor hash`, `parameter family`, and
`AST-hash subset` while explicitly routing hash granularity to Topic 013
(`debate/008-architecture-identity/final-resolution.md:135-153,177-180`). That
does not imply "ignore parameter distinctions until the behavioral layer." The
presence of `parameter family` in the pre-bucket contract means some parameter
semantics are already part of the structural gate. Freezing architecture-level
only granularity here risks collapsing distinctions that the upstream contract
deliberately preserved, while Topic 006's feature-family taxonomy is still open
(`debate/006-feature-engine/findings-under-review.md:34-40,76-77`).

Third, the proposed `2 gate + 3 characterization` split overruns Topic 017's live
ownership claim. Topic 018 routed "thresholds and proof-consumption rules" to
017/013 jointly, and Topic 017's dossier states that Topic 017 owns proof-bundle
consumption rules and exact numeric anomaly thresholds
(`debate/018-search-space-expansion/final-resolution.md:127-136,155-180`;
`debate/017-epistemic-search-policy/findings-under-review.md:426-435`). Claude's
mandatory-all model with two gate components is not just threshold methodology. It
is proof-consumption semantics. That is precisely the boundary still open with 017.

Fourth, pure population-relative anomaly thresholds are not yet proven as the
architecture-level rule. Relative normalization may be a useful calibration aid,
but Topic 017 still owns the active threshold values for the anomaly axes
(`debate/017-epistemic-search-policy/findings-under-review.md:430-435`). And pure
percentile logic becomes unstable in sparse populations or thin cells, which is
exactly where surprise handling matters most. Claude has therefore not shown that
"relative only" is safer than a hybrid rule with explicit sparsity guards.

The strongest surviving surface is narrower: Topic 013 must freeze explicit
versioned equivalence-threshold semantics and structural-hash granularity rules,
but it has not yet earned the right to freeze proof-component gating or pure
population-relative anomaly consumption on Topic 017's behalf. `Open`.

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-CA-01 | Convergence measurement framework | Thiếu sót | Open | A single primary rank-correlation metric plus a deterministic permutation test gives a reproducible convergence core, and a four-state hierarchy preserves more information than FULLY/PARTIALLY/NOT. | The metric depends on unresolved equivalence semantics, the stated permutation null is ill-posed, Topic 007 keeps same-archive subtype taxonomy open, and Topic 001 routed the numeric closure to 013 rather than to implementation. |
| X38-CA-02 | Stop conditions & diminishing returns | Thiếu sót | Open | An evidence-triggered `Δρ` plateau is strictly better than fixed ceilings because it measures actual information gain and separates genuine convergence from resource exhaustion. | The dossier was never count-only; `Δρ` does not subsume novelty, coverage, and winner stability, `convergence_stall` is not identical to `CEILING_STOP`, and Topic 001 already froze same-data ceiling + human override as part of the architecture. |
| X38-SSE-09 | Scan-phase correction law default | Thiếu sót | Open | BH is the right v1 default because scan is recall-oriented and later validation absorbs the extra false positives; cascade is below the architectural line. | Scan false positives change Stage 4 archive composition and budget/coverage flow before later gates, the "later gates make it cheap" citation overreaches the authority base, and Topic 003 still treats cascade as one of the live architectural options. |
| X38-SSE-04-THR | Equivalence + anomaly thresholds | Thiếu sót | Open | Conservative behavioral ρ, architecture-level structural hash, a 2+3 proof split, and percentile-based anomaly thresholds give a methodology-level default while leaving exact values flexible. | Versioned determinism means threshold drift changes equivalence semantics, Topic 008 does not support architecture-only bucketing, Topic 017 still owns proof-consumption and anomaly-threshold semantics, and pure percentile rules are not yet justified for sparse populations. |
