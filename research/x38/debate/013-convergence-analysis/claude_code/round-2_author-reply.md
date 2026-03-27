# Round 2 — Author Reply: Convergence Analysis

**Topic**: 013 — Convergence Analysis
**Author**: claude_code
**Date**: 2026-03-27
**Responds to**: `codex/round-1_rebuttal.md`
**Scope**: CA-01, CA-02, SSE-09, SSE-04-THR

**Artifacts read**:
  - All artifacts from round-1 opening critique
  - `debate/013-convergence-analysis/codex/round-1_rebuttal.md`
  - `debate/001-campaign-model/final-resolution.md`
  - `debate/007-philosophy-mission/final-resolution.md`
  - `debate/008-architecture-identity/final-resolution.md`
  - `debate/018-search-space-expansion/final-resolution.md`
  - `debate/017-epistemic-search-policy/findings-under-review.md`
  - `debate/006-feature-engine/findings-under-review.md`
  - `debate/003-protocol-engine/findings-under-review.md`
  - `debate/rules.md`
  - `debate/prompt_template.md`
  - `AGENTS.md`
  - `docs/online_vs_offline.md`
  - `x38_RULES.md`
  - `docs/design_brief.md`
  - `PLAN.md`

**MANDATORY RULE REMINDER**
1. §4: Attack the argument, not the conclusion.
2. §7: Steel-man is required before marking `Converged`.
3. §8: No soft concession language; every concession must be evidence-backed.
4. §12: No new topic creation after round 1.

---

## Framing

Codex's rebuttal follows a consistent pattern across all 4 issues: accept the
observation, reject the proposed mechanism. The observations rest on solid
upstream authority (Topics 001, 007, 008, 017, 018), and I do not contest them.
The debate is therefore about whether my proposed mechanisms are premature,
ill-specified, or scope-overreaching. I address each counter-argument below,
conceding where Codex's evidence compels correction and defending where the
counter-arguments do not survive scrutiny.

Three concessions are evidence-backed and I state them upfront:

1. **Permutation test ill-specification** (CA-01, counter-argument 3): Codex is
   right that permuting session labels under the null "sessions are
   interchangeable" does not change the pairwise agreement structure and
   therefore cannot falsify anything
   (`codex/round-1_rebuttal.md:104-109`). This is a genuine error in my
   round-1 formulation. I provide a corrected test below.

2. **CLAUDE.md citation without `[extra-archive]`** (SSE-09, counter-argument 2):
   I cited "7 downstream gates" from `CLAUDE.md` without the required
   `[extra-archive]` label per `debate/rules.md` §18
   (`codex/round-1_rebuttal.md:228-232`). The within-x38 evidence base
   supports the two-pass architecture independently of this citation.

3. **2+3 proof-component split overruns Topic 017** (SSE-04-THR,
   counter-argument 3): The gate vs. characterization classification is
   proof-consumption semantics. Topic 017 owns "Proof bundle consumption rules
   (what constitutes 'passing' a proof component)"
   (`017/findings-under-review.md:433`). I retract the 2+3 split and reframe
   013's obligation as completeness, not consumption.

These are not soft concessions — each is specifically compelled by evidence
Codex cited, as elaborated in each issue section below.

---

## Part A — Steel-Man Attempts

No issues are ready for convergence. All 4 issues have narrowed disagreement
surfaces through evidence-backed concessions and refined positions, but no
position has been fully resolved per §7(a)(b)(c). All remain Open.

---

## Part B — Continued Debate

### CA-01: Convergence measurement framework

Codex raises 4 counter-arguments. I address each in order.

**Counter-argument 1: Four-state taxonomy overruns Topic 007 subtype authority.**

Codex argues that splitting `PARTIALLY_CONVERGED` into `STRUCTURALLY_CONVERGED`
and `FAMILY_CONVERGED` freezes a subtype lattice while Topic 007 left same-
archive subtype taxonomy open (`007/final-resolution.md:94-95`: "Sub-type
taxonomy within same-archive categories is NOT frozen — dimensions remain open
for consuming topics (001, 010) to define as needed"). Codex further claims
entanglement with open taxonomy work in Topics 006 and 017
(`codex/round-1_rebuttal.md:85-90`).

This argument conflates two distinct design surfaces. Topic 007's open subtype
taxonomy is about **evidence classification**: how to sub-classify same-archive
evidence within the 3 frozen evidence types (coverage/process, deterministic
convergence, clean adjudication). My 4-state hierarchy is about **measurement
granularity**: at which identity level did sessions agree? This is a convergence
metric output, not an evidence subtype.

The distinction matters mechanistically. Evidence subtypes affect how Topic 003's
protocol engine classifies and routes evidence. Convergence granularity affects
how Topic 001's HANDOFF trigger interprets the convergence signal. These are
different consumers with different contracts. The convergence hierarchy consumes
Topic 008's frozen identity vocabulary (descriptor hash, parameter_family,
AST-hash subset — `008/final-resolution.md:136-137`), not Topic 007's open
evidence taxonomy.

Codex's claimed entanglement with Topics 006 and 017 does not survive evidence
check. The citation at `006/findings-under-review.md:76` specifies: "006 owns
feature-level taxonomy; 017 owns strategy-level descriptors. Must not conflict."
My convergence hierarchy uses **strategy-level identity** (family, architecture,
parameter), which maps to Topic 008's `parameter_family` field (frozen in
`008/final-resolution.md:136-137`), not Topic 006's feature families (trend,
volatility, location — `006/findings-under-review.md:34-39`). These are
different design surfaces with no dependency.

However, I accept Codex's narrower claim that a mandatory *expanded verdict
vocabulary* is not architecturally required at this stage. The measurement
framework can report convergence at each identity level (family, architecture,
parameter) without creating formal state names. This is operationally equivalent
— the information content is identical, and the state labels can be fixed in
implementation without architectural consequence.

**Narrowed position**: freeze mandatory multi-level convergence reporting at
(minimum) 3 granularity levels consuming Topic 008's identity vocabulary. The
exact state labels are secondary to the multi-level structure. The disagreement
is now about the *measurement pipeline* (metric choice + significance test),
not the verdict taxonomy.

**Counter-argument 2: Spearman ρ depends on unresolved equivalence semantics.**

Codex argues that `rank = K+1 for absent candidates` is a new semantic choice
that hard-codes how partial overlap is punished before SSE-04-THR settles
equivalence (`codex/round-1_rebuttal.md:98-101`).

I concede that the `rank = K+1` rule is premature. It depends on the comparison
domain contract (SSE-D-04 field 2), which defines which candidates are eligible
for cross-session comparison. Once the comparison domain is defined, absent-
candidate handling is specified by that contract, not by the convergence metric.

However, this does not invalidate Spearman ρ as the metric choice. Codex's
argument is that "the proposed primary metric depends on unresolved semantics."
But ANY rank-based metric will depend on the comparison domain — Jaccard, winner
voting, and Sharpe overlap all require knowing which candidates to compare.
The metric choice is architecturally separable from the comparison domain
semantics. Spearman ρ is the right metric class because:

1. It produces a continuous signal ρ ∈ [-1, 1], enabling threshold-based
   convergence levels — whatever those levels are.
2. It is a closed-form computation requiring no resampling, satisfying the
   offline paradigm's reproducibility requirement
   (`docs/online_vs_offline.md:12-25`).
3. It preserves ordinal information that Jaccard (set overlap) and winner
   voting (point estimate) discard.

The surviving position: freeze rank correlation as the metric class; defer
absent-candidate handling to the comparison domain contract (field 2 of
SSE-D-04). This is correct dependency ordering — the comparison domain is an
INPUT to the convergence metric, not a component of it.

**Counter-argument 3: Permutation test is ill-specified.**

Conceded. Permuting session labels under the null "sessions are interchangeable"
leaves the pairwise ρ structure unchanged
(`codex/round-1_rebuttal.md:104-109`). The stated test cannot falsify anything.
The error is in specifying the permutation target, not in the choice of
permutation testing.

**Corrected formulation**: The null hypothesis is "candidate rankings are
independent across sessions" — knowing a candidate's rank in session A gives
no information about its rank in session B. The permutation procedure: for
each session independently, randomly permute the assignment of ranks to
candidates, preserving (a) the set of candidates per session and (b) the rank
distribution {1, 2, ..., K}. Test statistic: mean pairwise Spearman ρ across
all session pairs. Under the null, each session's ranking is a random
permutation of the candidate set, so ρ values center near zero. P-value:
proportion of permutations producing mean ρ ≥ observed mean ρ.

This is equivalent to a permutation-based Kendall's W (coefficient of
concordance) test, which directly measures agreement among multiple rankers.
The test is seeded (deterministic permutation schedule) for reproducibility,
per the offline paradigm.

**Counter-argument 4: Re-deferral of numeric values.**

Codex is right that Topic 001 routed "Stop thresholds, same-data ceiling,
sessions-per-campaign" to Topic 013 (`001/final-resolution.md:168`), and I
cannot call these "calibration parameters" and push them downstream
(`codex/round-1_rebuttal.md:111-118`).

I clarify: the architecture should freeze **calibration procedures** that
produce numeric values deterministically given the data. This is specification,
not re-deferral. The procedures:

- **τ (convergence threshold)**: set at the α = 0.05 significance level of
  the corrected concordance test. τ is the critical ρ below which the null
  "no ranking agreement" is not rejected. The procedure (significance level
  + test type + permutation count) is frozen; the resulting τ value is
  deterministic per protocol/dataset.
- **K (top-K size)**: protocol-declared with framework range [5, 50] and v1
  default K = 10.
- **N_perm (permutation count)**: framework range [500, 10000], v1 default
  N_perm = 1000.

These are not bare constants — they are procedures with ranges and defaults.
The distinction matters: freezing τ = 0.7 (a fixed constant) cannot be
justified without empirical calibration on a specific candidate population.
Freezing the calibration procedure is specification; freezing an arbitrary
constant is guessing.

---

### CA-02: Stop conditions & diminishing returns

Codex raises 5 counter-arguments. I address each in order.

**Counter-argument 1: Straw target — the finding was multi-signal, not
count-only.**

Codex is partially right (`codex/round-1_rebuttal.md:147-152`). The round-0
finding names three distinct signals (information gain, novel candidate rate,
winner stability — `findings-under-review.md:99-104`). I overstated the
finding's position by framing it as "count-triggered vs evidence-triggered."
The finding already contains evidence elements.

I retract the "count-triggered" framing. However, the finding's open question
"Trần mặc định sessions per campaign? (3? 5? adaptive?)"
(`findings-under-review.md:136`) does frame the stop condition in count terms.
My Δρ proposal stands on its own merits as a unification framework, not as a
rebuttal of a count-only model.

**Counter-argument 2: Three signals are not "ordered projections."**

Codex argues that the 3 signals measure distinct things: novel candidate rate
is a frontier/coverage signal, winner stability is a leader-stability signal,
and convergence delta is an agreement-stability signal
(`codex/round-1_rebuttal.md:154-162`). Codex cites Topic 017's live tension
with coverage obligations (`017/findings-under-review.md:356-359`).

I concede that novel candidate rate is NOT subsumed by Δρ. Novel candidate
rate measures **frontier exploration** — whether the search is finding new
candidates. A campaign can have stable Δρ (convergence plateau) while still
finding novel candidates that rank below the top-K. Conversely, a campaign can
have zero novel candidates while Δρ is still shifting (existing candidates
re-ordering). These are mechanistically independent signals.

The architectural implication: convergence stop and coverage stop are
**separate signals with separate owners**:
- **Topic 013** owns convergence stop (Δρ-based): "has the ranking
  stabilized?"
- **Topic 017** owns coverage stop: "has the search space been adequately
  explored?"

The campaign stops when BOTH 013 and 017 signal exhaustion, OR when the hard
ceiling is hit. This separation correctly reflects the cross-topic ownership
boundary (`017/findings-under-review.md:357`: "013 owns convergence/stop; 017
defines coverage obligations").

On winner stability: I maintain this IS captured by ρ. If the top-1 candidate
is stable across M sessions, pairwise ρ at the top-1 position is necessarily
high. Winner stability is a necessary condition for high ρ, and high ρ
implies winner stability at every level including top-1. Winner stability is a
projection of ρ, not an independent signal.

**Counter-argument 3: convergence_stall ≠ CEILING_STOP.**

Codex argues that a campaign can stall before reaching the ceiling, and can
hit the ceiling without stalling (`codex/round-1_rebuttal.md:164-171`).

I concede this distinction. They are operationally different conditions:

- **convergence_stall**: Δρ < ε for M consecutive sessions. The convergence
  picture has plateaued — adding sessions does not change it. This can fire
  at session 4 of a 10-session budget.
- **CEILING_STOP**: session count reaches the hard ceiling. Budget is
  exhausted — convergence may or may not have been reached.

Both can trigger HANDOFF, but with different dossier contents:
- convergence_stall → HANDOFF with `convergence_summary` (complete). The
  campaign produced an answer (possibly `NO_ROBUST_IMPROVEMENT`).
- CEILING_STOP → HANDOFF with `convergence_summary` (partial) + extension
  request. The campaign ran out of sessions — the answer is incomplete.

I retract my equation of convergence_stall = CEILING_STOP. The stop condition
framework must produce both signals with distinct HANDOFF routing.

**Counter-argument 4: Hard ceiling is architectural, not safety-valve.**

Codex is right (`codex/round-1_rebuttal.md:173-179`). Topic 001 froze
same-data ceiling + explicit human override + mandatory purpose declaration as
part of the same-data governance law
(`001/final-resolution.md:113-115,147-160`). I characterized the hard ceiling
as a "safety valve" and "resource bound" which understates its architectural
role.

I concede: the hard ceiling is a first-class architectural component of the
stop condition framework, not a fallback around the data-driven stop rule.
The framework must make the ceiling operational with explicit human-override
mechanics per Topic 001's same-data governance.

**Counter-argument 5: Re-deferral of ε, M, hard ceilings.**

Same principle as CA-01: calibration procedures with ranges and defaults. The
framework freezes:

- **ε (stall threshold)**: defined as the significance level of the
  concordance test (α = 0.05 → ε is the critical Δρ below which the null
  "no improvement" is not rejected). Procedure frozen; value is
  deterministic per protocol.
- **M (consecutive stalled sessions)**: framework range [2, 5], v1 default
  M = 3.
- **Within-campaign ceiling**: framework range [3, 20] sessions, protocol-
  declared within range. v1 default determined by `design_brief.md` campaign
  properties.
- **Same-data campaign ceiling**: framework range [2, 5] campaigns, v1
  default = 3. Ceiling hit → mandatory human override per Topic 001.

---

### SSE-09: Scan-phase correction law default

Codex raises 3 counter-arguments. I address each in order.

**Counter-argument 1: Scan false positives shape Stage 4 archive composition.**

Codex argues that false discoveries at Stage 3 distort which cells retain
slots, which neighborhoods get probed, and which anomalies consume
queue/budget attention (`codex/round-1_rebuttal.md:218-225`). This is a
structural exploration cost, not just wasted compute.

I accept the premise: Stage 3 false positives do have a non-compute cost
through archive composition. However, the question is whether this cost
favors Holm (FWER) over BH (FDR) as default. The answer depends on the
asymmetry of errors in the cell-elite architecture:

- **False discovery in a populated cell**: cheap. The cell already has genuine
  candidates. The false discovery competes for a slot but is likely eliminated
  by Stage 4 pruning (orthogonal pruning tests candidates against each other
  within cells — `docs/design_brief.md:62-74`). The slot is temporarily
  occupied and then freed.

- **False rejection of a genuine candidate in a sparse cell**: expensive. The
  candidate may be the ONLY representative of that cell. Holm's stricter
  threshold is more likely to reject genuine candidates in sparse cells, where
  multiplicity corrections hit hardest (many comparisons relative to few
  discoveries). The cell permanently loses its sole candidate, distorting
  coverage.

The asymmetry persists: BH's false discoveries in populated cells are
self-correcting (downstream stages prune them), while Holm's false rejections
in sparse cells are permanent (no later stage can recover a candidate
rejected at Stage 3). This is precisely the argument that motivates FDR over
FWER in high-throughput screening contexts — downstream validation handles
false discoveries, but nothing recovers false rejections.

Codex's archive-composition concern is real but does not flip the default.
BH remains the right v1 default because the asymmetric cost structure favors
recall in the scan phase. The structural cost of false discoveries is lower
than the structural cost of false rejections in the cell-elite architecture.

**Counter-argument 2: CLAUDE.md citation error.**

Conceded. The within-x38 evidence base that supports the two-pass
architecture independently:
- `docs/design_brief.md:55-72` (8-stage pipeline, scan → validation
  structure)
- `PLAN.md:633-670` (pipeline stages with explicit scan/validation
  separation)
- `018/final-resolution.md:86-99` (7-field interface confirming stage
  separation)

These sources establish the same architectural claim without extra-archive
evidence.

**Counter-argument 3: Cascade is not just implementation detail.**

Codex argues that Topic 003 treats cascade as one of the live architectural
options (`003/findings-under-review.md:65-67`: "FDR (Benjamini-Hochberg)?
Step-down (Holm)? Hay cascade design (shortlist → holdout) tự nó đã đủ?").

I maintain that cascade and BH/Holm are on different architectural axes:

- **Correction law** (BH/Holm): which error rate is bounded. A statistical
  philosophy choice.
- **Test structure** (flat/cascade): how tests are organized across stages.
  A cascade can use BH at Stage 3 and Holm at Stage 6 — the two are
  composable.

Topic 003's framing presents FDR, Holm, and cascade as alternatives. This is
a false trichotomy. Cascade is not an alternative TO FDR/Holm — it is a
structure WITHIN which FDR/Holm is applied at each level.

However, I accept that the interaction between correction law and test
structure IS architecturally significant: the correction law at Stage 3
determines how many candidates survive to Stage 4, which constrains Stage 4's
test structure. BH at Stage 3 → more survivors → larger Stage 4 candidate
set. Holm at Stage 3 → fewer survivors → smaller Stage 4 set (possibly
undermining cell diversity). This interaction should be documented as a
cross-topic tension between 013 and 003, rather than collapsed into either
topic's sole decision.

SSE-D-04 field 5 (`scan_phase_correction_method`) is about the correction
LAW, not the test structure. These are separable decisions: 013 owns the
correction law choice (field 5), 003 owns the protocol engine's stage
transition structure. Both interact; neither subsumes the other.

---

### SSE-04-THR: Equivalence + anomaly thresholds

Codex raises 4 counter-arguments. I address each in order.

**Counter-argument 1: Floating threshold + versioned determinism conflict.**

Codex argues that if the threshold floats with each protocol's observed
distribution, equivalence semantics drift with the candidate population,
violating Topic 018's versioned determinism rule
(`018/final-resolution.md:213-214`: "thresholds are part of the equivalence
definition and must be versioned")
(`codex/round-1_rebuttal.md:266-274`).

This conflates calibration-time and run-time behavior. The "natural gap"
calibration is performed ONCE per protocol version, during protocol
specification. It produces a fixed threshold that becomes part of the
protocol's equivalence definition. The procedure:

1. Protocol specifies candidate population and computes pairwise ρ
   distribution.
2. Calibration procedure identifies the threshold (natural gap or default
   percentile).
3. Threshold is frozen into the protocol's field 4 (`equivalence_method`)
   declaration.
4. Subsequent sessions use the frozen threshold — no runtime drift.

This satisfies versioned determinism: same protocol version → same
threshold → same equivalence decisions. Different protocol versions may
have different thresholds because different protocols with different
candidate populations SHOULD have different equivalence boundaries. Topic
018's rule explicitly supports this — the threshold is versioned WITH the
protocol (`018/final-resolution.md:213-214`). Changing the threshold
requires a new protocol version.

Codex's concern is valid for a naive runtime-adaptive threshold. My proposal
is a calibration-time-frozen threshold. The distinction resolves the
apparent conflict.

**Counter-argument 2: Architecture-only structural hash overreads Topic 008.**

Codex argues that `parameter_family` in Topic 008's pre-bucket fields means
"some parameter semantics are already part of the structural gate," and that
my architecture-level-only granularity risks collapsing distinctions the
upstream contract deliberately preserved
(`codex/round-1_rebuttal.md:276-285`).

`parameter_family` is a family-level descriptor, not individual-parameter-
level. Topic 008's structural pre-bucket fields are: descriptor hash
(architecture structure), parameter_family (family grouping), AST-hash
subset (structural composition) — `008/final-resolution.md:136-137`. None
capture individual parameter VALUES (e.g., slow=120 vs slow=140).

My "architecture-level granularity" means: same descriptor hash + same
parameter_family + same AST-hash subset = same structural bucket. This is
exactly what Topic 008's fields define. The `parameter_family` field groups
strategies by family membership (e.g., "momentum_crossover"), not by
individual parameter values. A family of "momentum_crossover" groups ALL
momentum crossover strategies regardless of specific parameter values.
Individual parameter differences are handled by the behavioral layer
(nearest-rival audit), which is precisely the hybrid design's intent
(`018/final-resolution.md:206-211`).

Codex's citation of Topic 006's feature-family taxonomy
(`006/findings-under-review.md:34-40,76-77`) is not relevant to this point.
Line 76 clarifies: "006 owns feature-level taxonomy; 017 owns strategy-level
descriptors." My convergence hierarchy consumes strategy-level identity
(Topic 008's vocabulary), not feature-level taxonomy (Topic 006's
vocabulary). The overlap between 006 and 017 noted at line 76 is between
*feature families* and *phenotype descriptors* — neither of which is the
structural pre-bucket fields I consume.

**Counter-argument 3: 2+3 proof split overruns Topic 017's ownership.**

Conceded. Topic 017's `findings-under-review.md:433` states: "Proof bundle
consumption rules (what constitutes 'passing' a proof component)." The gate
vs. characterization classification is a consumption decision — which
components are must-pass vs. informational is precisely "what constitutes
'passing'." This is 017's ownership, not 013's.

I retract the 2+3 split. Topic 013's obligation from SSE-D-05 is narrower:
specify the **completeness minimum** — how many components must be
*attempted*. Topic 013 freezes: "all components in the working minimum
inventory (currently 5 per `018/final-resolution.md:166-167`) must be
attempted for every candidate entering the proof bundle stage." Topic 017
decides which components are gates (must-pass) vs. characterization
(informational). This corrects the ownership overreach while preserving
013's completeness obligation.

The shared ownership boundary (per `018/final-resolution.md:173`:
"Thresholds and proof-consumption rules: 017/013 own") is now cleaner:
013 owns completeness (how many, all attempted), 017 owns consumption
(which pass/fail, what constitutes passing).

**Counter-argument 4: Population-relative anomaly thresholds unstable in
sparse populations.**

Codex is right that percentile-based thresholds become meaningless in small
populations (`codex/round-1_rebuttal.md:300-302`). The 5th percentile of 3
candidates is the minimum value — not a meaningful outlier threshold. This is
a statistical fact, not a design preference.

I amend: a **hybrid rule** with explicit sparsity guards.

- **N ≥ N_min (sufficient population)**: population-relative thresholds
  (percentile-based, per my original proposal). Preserves asset-agnostic
  adaptability where the population statistics are meaningful.
- **N < N_min (sparse population)**: absolute floor thresholds calibrated
  from the v1 protocol's empirical data. Protocol-declared constants that
  provide meaningful outlier detection even in thin cells.
- **N_min**: protocol-declared with framework default (v1 default = 20).
  Below this count, percentile statistics are unreliable.

The absolute floor thresholds for sparse populations are calibration
parameters owned by Topic 013 — they are calibrated during v1 protocol
development and frozen into the protocol version per versioned determinism
(same calibration-time-frozen semantics as counter-argument 1).

This hybrid rule addresses Codex's sparsity concern while preserving the
asset-agnostic property of relative thresholds where they are statistically
grounded. The sparsity guards are not optional scaffolding — they are part of
the threshold methodology.

**Ownership boundary with 017 (refined)**: 013 defines the threshold
**methodology** (hybrid relative/absolute, sparsity guard, calibration
procedure). 017 defines the threshold **values** for each anomaly axis
within 013's methodology, and owns consumption semantics (what happens to
anomalous candidates). Per `018/final-resolution.md:173`: "Thresholds and
proof-consumption rules: 017/013 own" — shared ownership, split by
methodology (013) vs. axis-specific values and consumption (017).

---

## Cross-topic tensions (updated)

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 017 | ESP-01, ESP-04 | Coverage metrics overlap convergence measurement (CA-01). Novel candidate rate is 017's coverage signal, not 013's convergence signal (conceded R2). Budget governor coverage obligation extends campaigns independently of 013's convergence stop. | 013 owns convergence stop (Δρ-based); 017 owns coverage stop (novel candidate rate). Campaign stops when both signal exhaustion OR hard ceiling hit. |
| 017 | ESP-04 | Proof-component gate/characterization split is 017's consumption decision, not 013's (conceded R2). 013 owns completeness minimum only. | 017 owns consumption semantics; 013 owns completeness. Shared per `018/final-resolution.md:173`. |
| 017 | ESP-04 | Anomaly axis threshold methodology (013) vs. axis-specific numeric values (017). Sparsity guard methodology must be compatible with 017's per-axis value choices. | 013 defines methodology (hybrid relative/absolute); 017 sets values within methodology. |
| 018 | SSE-09, SSE-04-THR | Routing confirmed. SSE-D-09 and SSE-D-04/05 provide binding interface constraints. | 013 implements within upstream-frozen interfaces. No tension — clean handoff. |
| 008 | SSE-04-IDV | 013's convergence hierarchy consumes 008's frozen identity vocabulary (descriptor hash, parameter_family, AST-hash subset). Behavioral equivalence threshold must be compatible with structural pre-bucket. | 008 owns structural pre-bucket fields; 013 owns behavioral semantics. 2-layer hybrid design is the compatibility mechanism. |
| 003 | F-05 | Correction law (013, field 5) interacts with test structure (003, stage transitions). BH at Stage 3 → more survivors → larger Stage 4 candidate set. Choice of correction law constrains 003's cascade/flat decision. | 013 owns correction law; 003 owns stage transition structure. Interaction documented, neither subsumes the other. |
| 001 | D-03, D-16 | Topic 001 deferred numeric convergence floors and session ceilings to 013. HANDOFF triggers `{convergence_stall, methodology_gap}` depend on 013's stop condition signals. convergence_stall and CEILING_STOP are distinct signals (conceded R2) producing different HANDOFF dossier contents. | 013 produces both signals; 001 consumes via HANDOFF trigger vocabulary. |
| 007 | D-01 | `NO_ROBUST_IMPROVEMENT` as valid campaign exit depends on 013's convergence analysis being valid — convergence was measured, answer is "nothing passes the bar". | 007 provides constraint; 013 operationalizes via `convergence_stall` + no robust candidate path. |

---

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-CA-01 | Convergence measurement framework | Thiếu sót | Open | "Topic 013 should freeze mandatory multi-level reporting and a common comparison-domain contract, but NOT one canonical Spearman-plus-permutation pipeline or expanded verdict taxonomy." | Multi-level reporting and comparison-domain contract are accepted. The narrowed defense: (1) rank correlation (Spearman ρ) is the right metric CLASS — continuous, closed-form, ordinal-preserving — independent of which comparison domain is chosen, and no alternative metric has been proposed; (2) corrected concordance test (permutation on candidate-rank assignments, not session labels) replaces the ill-specified original; (3) calibration procedures with ranges and defaults are specification, not re-deferral — Topic 001 routed "numeric convergence rules" here, and rules include procedures. |
| X38-CA-02 | Stop conditions & diminishing returns | Thiếu sót | Open | "Topic 013 should freeze a multi-signal stop framework with explicit separation between convergence-based stop and ceiling-based stop, preserving Topic 001's hard ceiling + human-override law. Δρ cannot safely absorb novelty, coverage, and winner stability into one signal." | Convergence/coverage separation accepted: novel candidate rate is 017's coverage signal, not 013's convergence signal. convergence_stall ≠ CEILING_STOP accepted (distinct routing). Hard ceiling as first-class architecture accepted. The narrowed defense: (1) Δρ as convergence stop (NOT coverage stop) remains the correct signal for ranking stabilization; (2) winner stability IS a projection of ρ (stable top-1 ⇒ high top-1 ρ); (3) calibration procedures (ε, M, ceilings as ranges + defaults + significance-level-based thresholds) are specification, not re-deferral. |
| X38-SSE-09 | Scan-phase correction law default | Thiếu sót | Open | "BH is not yet justified as default because scan false positives are not merely wasted compute — they distort Stage 4 archive composition, budget/coverage flow, and Topic 003 still treats cascade as an architectural option." | Archive-composition cost is real but asymmetric: BH false discoveries in populated cells are self-correcting (downstream pruning), while Holm false rejections in sparse cells are permanent (no recovery). Cell-elite architecture makes sparse-cell loss more costly than populated-cell contamination. Cascade is on a different axis (test structure, owned by 003) from correction law (error rate philosophy, owned by 013) — they interact but do not subsume each other. CLAUDE.md citation error conceded; within-x38 evidence base (`design_brief.md:55-72`, `PLAN.md:633-670`, `018/final-resolution.md:86-99`) independently supports two-pass architecture. |
| X38-SSE-04-THR | Equivalence + anomaly thresholds | Thiếu sót | Open | "Calibration-time-frozen thresholds still drift with candidate population across protocol versions, Topic 008 does not support architecture-only bucketing, Topic 017 owns proof-consumption semantics, and pure percentile rules fail in sparse populations." | (1) Cross-version threshold difference is BY DESIGN — different protocols with different populations SHOULD have different boundaries, versioned per `018/final-resolution.md:213-214`. Within a protocol version, no drift. (2) Topic 008's pre-bucket fields (descriptor hash, parameter_family, AST-hash subset) ARE architecture-level — `parameter_family` is family grouping, not individual parameter values. (3) 2+3 split conceded to 017; 013 owns completeness minimum only. (4) Hybrid rule with sparsity guards (N ≥ N_min → relative; N < N_min → absolute floor) addresses the sparse-population instability while preserving asset-agnostic adaptability. |
