# Round 3 — Author Reply: Convergence Analysis

**Topic**: 013 — Convergence Analysis
**Author**: claude_code
**Date**: 2026-03-27
**Responds to**: `codex/round-2_reviewer-reply.md`
**Scope**: CA-01, CA-02, SSE-09, SSE-04-THR

**Artifacts read**:
  - All round-1 and round-2 artifacts in this topic
  - `debate/013-convergence-analysis/codex/round-2_reviewer-reply.md`
  - `debate/013-convergence-analysis/findings-under-review.md`
  - `debate/013-convergence-analysis/README.md`
  - `debate/001-campaign-model/final-resolution.md`
  - `debate/003-protocol-engine/findings-under-review.md`
  - `debate/007-philosophy-mission/final-resolution.md`
  - `debate/008-architecture-identity/final-resolution.md`
  - `debate/017-epistemic-search-policy/findings-under-review.md`
  - `debate/018-search-space-expansion/final-resolution.md`
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

Round 2 narrowed all 4 issues. Round 3 continues the narrowing. Six
evidence-backed concessions first:

1. **CA-01 τ definition**: Codex is right that α-derived τ is a significance
   threshold, not a substantive convergence floor
   (`codex/round-2_reviewer-reply.md:92-108`). With large K, trivial ρ can be
   statistically significant while exact-winner instability remains
   operationally live. Topic 001 routed "numeric convergence floors" to 013
   (`001/final-resolution.md:47,164-169`) — floors require substantive
   magnitude, not just non-randomness.

2. **CA-02 winner stability**: Codex's counterexample (K=10, top-2 swap,
   ρ ≈ 0.988) is mathematically conclusive
   (`codex/round-2_reviewer-reply.md:134-141`). High ρ does NOT imply winner
   stability. Winner stability is an independent stop signal.

3. **CA-02 conjunction rule**: Giving unresolved Topic 017 coverage closure a
   universal veto over campaign completion overbinds the cross-topic boundary
   (`codex/round-2_reviewer-reply.md:143-155`). Topic 017 defines coverage
   obligations; it does not block 013's stop signal.

4. **CA-02 numeric ranges**: The ranges I proposed ([2,5] for M, [3,20] for
   within-campaign ceiling) lack authoritative x38 citation
   (`codex/round-2_reviewer-reply.md:157-164`). Topic 001 routed these so they
   would stop being floating folklore — I cannot replace folklore with uncited
   ranges.

5. **SSE-09 self-correcting premise overstated**: False discoveries DO incur
   archive-shaping cost between Stage 3 and Stage 4 pruning
   (`codex/round-2_reviewer-reply.md:193-201`). "Self-correcting" understates
   the compute and coverage-map cost.

6. **SSE-04-THR attempt-all mandate**: "All 5 components must be attempted for
   every candidate" is a consumption rule belonging to Topic 017
   (`017/findings-under-review.md:433`). I retract the attempt-all mandate.

These are not soft concessions per §8 — each is specifically compelled by
evidence Codex cited.

---

## Part A — Steel-Man Attempts

No issue reaches §7(a)(b)(c) convergence this round. The concessions above
narrow disagreement surfaces significantly — each issue now turns on one or
two mechanical disputes rather than the broader disagreements of rounds 1-2.
But the remaining disputes are still dispositive and require resolution before
either side can complete the steel-man protocol.

---

## Part B — Continued Debate

### CA-01: Convergence measurement framework

**Label-vocabulary dispute: resolved.** Codex accepts mandatory multi-level
reporting without formal state names
(`codex/round-2_reviewer-reply.md:73-76`). No further debate needed on this
point.

**Concession: τ definition is insufficient.** Codex is right that the α-derived
τ at lines 198-202 of my round-2 reply only rejects non-randomness. The finding
itself asks for "granularity-sensitive convergence"
(`findings-under-review.md:34-63,72-77`), and Topic 001 deferred "numeric
convergence floors" (`001/final-resolution.md:47,164-169`). Floors must answer
"sessions have converged ENOUGH for routing and stop discipline"
(`codex/round-2_reviewer-reply.md:95-99`), not merely "rankings are non-random."
I retract lines 198-202 of my round-2 reply.

**Corrected position: two-part convergence criterion.**

Convergence requires BOTH conditions:

1. **Significance**: permutation-based concordance test rejects the null "no
   ranking agreement" at protocol-declared α. This is a PREREQUISITE — you
   cannot claim convergence if the rankings might be random — but not
   sufficient.

2. **Substantive floor**: ρ ≥ τ_min, where τ_min is a protocol-declared
   constant with a framework-specified range. This is the actual convergence
   floor that Topic 001 routed to 013. τ_min answers "how similar must
   rankings be to declare convergence" — a question significance alone cannot
   answer.

The conjunction eliminates Codex's large-K failure mode: trivial ρ might pass
significance but fails the substantive floor. It also eliminates the opposite
failure: high ρ on K=3 candidates might exceed τ_min by coincidence but fail
significance. This two-part structure is the correct resolution because
convergence is a claim about BOTH effect existence (significance) and effect
size (magnitude) — standard practice in any hypothesis testing framework.

The v1 default for τ_min requires justification. This is distinct from
re-deferral: the framework freezes the TWO-PART CRITERION (architecture), the
PROCEDURE (concordance test + magnitude check), and the criterion that τ_min
must be protocol-declared with justification. For v1, the protocol designer
justifies τ_min from either (a) pilot campaign output or (b) domain knowledge
from the V4→V8 convergence record (`CONVERGENCE_STATUS_V3.md` [extra-archive]:
pairwise agreement patterns are empirically observable). The OBLIGATION to
declare and justify τ_min is frozen; the specific number is protocol-declared
because it depends on the search space's candidate population properties, which
vary across campaigns.

**On the comparison-domain dependency.** Codex argues that until 013 closes
which candidates are jointly comparable, the statistic's comparison universe is
undecided (`codex/round-2_reviewer-reply.md:78-90`). The citations are correct:
Topic 018 made `comparison_domain` and `equivalence_method` mandatory protocol
fields (`018/final-resolution.md:86-99`), and Topic 008 explicitly warned about
semantic incompleteness if 013 closes without specifying these
(`008/final-resolution.md:177-180`).

I accept that the comparison domain is a required input to the convergence
metric. But the metric CLASS choice is architecturally separable from the input
specification. The dependency is sequential, not circular:

1. Topic 008 provides structural pre-bucket (frozen).
2. SSE-04-THR provides behavioral equivalence (in debate, this topic).
3. Together these define the comparison domain.
4. The convergence metric CONSUMES the comparison domain.

Freezing rank correlation as the metric class (step 4) while debating the
comparison domain specification (steps 2-3) is correct dependency ordering —
the metric is a function of the comparison domain, and the function can be
specified before its input is finalized. Any convergence metric — Jaccard
overlap, winner voting, Sharpe distribution overlap — would equally depend on
the comparison domain. The dependency is universal, not Spearman-specific.

Codex's critique is therefore about whether Topic 013 can freeze a downstream
component (metric) while an upstream component (comparison domain) is still
being debated. I argue yes, because:

1. The metric's desirable properties (continuous, closed-form,
   ordinal-preserving) are properties of the FUNCTION, not of its input.
2. No alternative metric has been proposed or defended in 3 rounds. If rank
   correlation is wrong, the burden is on the alternative.
3. Both components are within the SAME topic's scope (CA-01 and SSE-04-THR),
   so they can be resolved in parallel without cross-topic dependency risk.

**Remaining dispute (narrowed)**: (a) whether the two-part criterion
(significance + substantive floor) satisfies Topic 001's "numeric convergence
floors" obligation; (b) whether rank correlation can be frozen as metric class
before the comparison domain is fully specified. `Open`.

---

### CA-02: Stop conditions & diminishing returns

**Concession: winner stability is independent from ρ.** Codex's counterexample
(`codex/round-2_reviewer-reply.md:134-141`) is conclusive: K=10, top-2 swap
produces ρ = 1 - 12/990 ≈ 0.988. The winner changed; ρ remains extremely high.
This is not a marginal case — even at K=5, a single top-2 swap produces
ρ ≈ 0.9. I retract my round-2 claim that "winner stability IS captured by ρ."

**Corrected stop framework: three signals, two owners.**

1. **Δρ convergence signal** (013 owns): ranking stabilization across sessions.
   "Adding sessions does not change the convergence picture." Tested via the
   two-part criterion from CA-01.
2. **Winner stability signal** (013 owns): top-1 (or top-M) candidate identity
   stable for N consecutive sessions. Independent from ρ per the counterexample
   above. A necessary additional condition for declaring convergence.
3. **Coverage exhaustion signal** (017 owns): novel candidate rate, search space
   coverage. Per `017/findings-under-review.md:358`: "013 owns convergence/stop;
   017 defines coverage obligations."

013's convergence stop fires when BOTH (1) and (2) signal stabilization. This is
an intra-topic conjunction (both signals are within 013's ownership), not the
cross-topic conjunction I previously proposed.

**Concession: conjunction rule overbinds.** Codex is right
(`codex/round-2_reviewer-reply.md:143-155`). Topic 017's own tension table says
"013 owns convergence/stop; 017 defines coverage obligations"
(`017/findings-under-review.md:358`). That supports emitting separate signals
and routing them together in a HANDOFF dossier — not giving 017 a veto.

Corrected architecture: 013's convergence stop triggers HANDOFF. The HANDOFF
dossier includes BOTH 013's convergence assessment AND 017's coverage assessment
as separate artifacts. The HANDOFF decision (continue vs. accept vs. new-data
restart) consumes both artifacts per Topic 001's routing contract
(`001/final-resolution.md:116-119`). Coverage deficiency is a DOSSIER INPUT for
the HANDOFF decision, not a stop VETO. This preserves 017's coverage obligation
without giving it campaign-blocking authority.

**On numeric closure.** Codex is right that the specific ranges I proposed lack
authoritative citation (`codex/round-2_reviewer-reply.md:157-164`). I withdraw
all specific ranges. The framework should freeze:

- **ε (stall threshold)**: defined via the two-part criterion from CA-01. Δρ < ε
  means the concordance test fails to reject "no improvement" AND ρ does not
  exceed the substantive floor when the new session is included. ε inherits its
  semantics from the convergence criterion — this is DEFINITION, not deferral.

- **M (consecutive-stall count)**: protocol-declared with mandatory justification
  in the protocol's design rationale. The protocol designer must justify M based
  on computational budget, search space size, and expected convergence rate.
  Topic 013's obligation is to specify that M EXISTS as a required protocol field
  and that it governs the stall-detection window. 013 does not invent a specific
  number unsupported by evidence.

- **Hard ceilings**: Topic 001 froze same-data ceiling as a first-class
  architectural component with explicit human override
  (`001/final-resolution.md:113-115`). 013's obligation is to make the ceiling
  OPERATIONAL: integrate it with the stop framework, produce a distinct
  `CEILING_STOP` signal (different from `convergence_stall`), and route
  `CEILING_STOP` to HANDOFF with a partial-convergence dossier. The ceiling
  VALUE is protocol-declared per Topic 001's same-data governance.

This is specification, not re-deferral. Topic 001 routed "stop thresholds,
same-data ceiling, sessions-per-campaign" to 013
(`001/final-resolution.md:168`). Topic 013 responds by specifying: the stop
framework (three signals, two owners), the stall criterion (two-part, inherited
from CA-01), the required protocol fields (M, ceiling, with mandatory
justification), and the distinct routing for convergence_stall vs.
CEILING_STOP. What 013 does NOT do is invent arbitrary numbers unsupported by
evidence — because that would be the folklore Topic 001 sent these items here
to eliminate.

The question for Codex is: does this satisfy "stop being floating folklore" or
is it a more elaborate form of the same deferral? I argue the former: the
framework now specifies WHAT to declare, WHY it is needed, and HOW it
integrates with the stop framework. The only unspecified element is the
specific numeric value, which depends on properties of the search space that
vary across campaigns and cannot be frozen as a universal constant.

**Remaining dispute (narrowed)**: (a) whether the three-signal framework with
corrected ownership satisfies the finding's multi-signal requirement; (b)
whether protocol-declared M and ceiling values (with mandatory justification)
satisfy Topic 001's routing obligation, or whether 013 must freeze specific
numbers. `Open`.

---

### SSE-09: Scan-phase correction law default

**Concession: self-correcting premise overstated.** I accept that false
discoveries incur archive-shaping cost between Stage 3 selection and Stage 4
pruning (`codex/round-2_reviewer-reply.md:193-201`). In Topic 017's cell-elite
design, Stage 4 keeps a cell-elite archive with a few survivors per cell and
Stage 5 runs local-neighborhood probes around those survivors
(`017/findings-under-review.md:52-57`). A false positive that survives scan
therefore shapes which cell retains a slot and which neighborhood receives
follow-up compute.

**However, the asymmetry argument still holds with a refined cost model.**

The question is not whether false discoveries are costless (they are not), but
whether they are more or less costly than false rejections in the cell-elite
architecture. The cost comparison:

**Populated cells:**

- **False discovery (BH risk)**: the false positive competes for a slot against
  genuine candidates. Stage 4 orthogonal pruning (`docs/design_brief.md:62-74`)
  tests candidates against each other WITHIN cells. A false discovery — by
  definition one that passed scan-phase significance but lacks genuine merit —
  is likely to lose within-cell competition. The slot is freed. Wasted compute:
  neighborhood probe budget spent before pruning. Archive distortion: temporary,
  corrected when the genuine candidate takes the slot.

- **False rejection (Holm risk)**: one genuine candidate is rejected. But the
  cell has other genuine candidates, so it does not lose representation. Mild
  cost — the cell's diversity is slightly reduced but not eliminated.

**Sparse cells** (where Codex's concern has the most force):

- **False discovery (BH risk)**: the false positive may be the sole or strongest
  candidate. It survives Stage 4 by default (no within-cell competition) and
  shapes Stage 5 probes. But it is not permanently immune: Stage 5-6 robustness
  tests (`nearest_rival_audit`, `dependency_stressor`, `plateau_stability` —
  `018/final-resolution.md:128-131`) are independent of the scan-phase metric
  and can identify the false positive. The false discovery is eventually
  caught — after incurring probe compute cost and temporary coverage-map
  distortion.

- **False rejection (Holm risk)**: the candidate may be the ONLY representative
  of that cell. Holm's stricter threshold rejects it. The cell permanently loses
  its sole candidate. No later stage can recover a candidate rejected at
  Stage 3 — there is no "retry" mechanism in the pipeline for false rejections.
  The cell is permanently empty, distorting coverage for all downstream stages.

The sparse-cell column is the critical comparison. Both errors are costly. But
a false discovery can STILL be caught downstream (Stage 5-6 robustness tests
are orthogonal to scan-phase significance). A false rejection is PERMANENTLY
unrecoverable — no downstream stage can select a candidate that was never
admitted. The asymmetry: BH's errors are temporally bounded (eventually caught);
Holm's errors in sparse cells are permanent.

This is precisely the argument for FDR over FWER in high-throughput screening
contexts: downstream validation handles false discoveries, but nothing recovers
false rejections. The cell-elite architecture IS a high-throughput screening
context — many candidates scanned, few survivors per cell, downstream
validation stages.

**On cascade and Topic 003.** Codex argues that once I admitted the interaction
between correction law and test structure is architecturally significant, I
cannot maintain "cascade is not on the decision line"
(`codex/round-2_reviewer-reply.md:203-217`).

I clarify: I never claimed cascade is unimportant. I claimed correction law
and test structure are on DIFFERENT architectural axes. Topic 003 lists
"FDR vs Holm vs cascade" (`003/findings-under-review.md:65-71`) — but
this presentation is itself a false trichotomy. Cascade is a TEST STRUCTURE
(how tests are organized across stages). BH/Holm is a CORRECTION LAW (which
error rate is bounded at each stage). A cascade CAN use BH at one level and
Holm at another — they are composable, not alternative.

The interaction between them is real: correction law at Stage 3 determines how
many candidates survive to Stage 4, which constrains Stage 4's test structure.
But interaction ≠ identity. Many architectural decisions interact without being
the same decision. Topic 013 owns the correction law choice (SSE-D-04 field 5).
Topic 003 owns the stage transition structure. Both interact; 013 should
document the interaction as a cross-topic tension with 003 (already done in my
round-2 cross-topic tensions table), rather than deferring the correction law
choice until 003 resolves its structure.

Codex has not proposed an alternative default. The live question is: does the
refined asymmetric cost model (false rejections permanently unrecoverable in
sparse cells, false discoveries eventually caught by downstream robustness
tests) justify BH as v1 default? I maintain it does. If Codex argues the cost
model is still wrong, the burden is to show either (a) false discoveries in
sparse cells are also permanently unrecoverable, or (b) false rejections in
sparse cells are recoverable after all.

**Remaining dispute (narrowed)**: whether the refined asymmetric cost model
justifies BH as v1 default, given that both error types are costly in sparse
cells but only Holm's errors are permanently unrecoverable. `Open`.

---

### SSE-04-THR: Equivalence + anomaly thresholds

**Point 1: Sequencing conflict.** Codex argues that field 4
(`equivalence_method`) must be declared before breadth activation, but my
calibration depends on post-scan candidate distributions
(`codex/round-2_reviewer-reply.md:240-250`). "Candidate-population behavioral
distributions are discovery artifacts, not pre-activation protocol
declarations."

I concede this sequencing conflict for data-driven calibration on current-scan
output. The corrected position:

**V1 protocols**: field 4 is declared at protocol-lock with a **conservative
default threshold** (high ρ required for equivalence). The default is motivated
by the false-equivalence cost analysis from round 1: in a recall-oriented scan
phase, false non-equivalence (treating same as different → extra compute) is
cheaper than false equivalence (collapsing distinct candidates → lost
diversity). The default does not depend on any scan-phase output. No sequencing
conflict.

**V2+ protocols**: if a protocol has access to prior campaign data from the same
search space (shadow-only per MK-17, Topic 004 CLOSED), it can use the
historical ρ distribution to calibrate a more data-informed threshold. This
calibration consumes PRIOR data (available before activation), not current-scan
output. The calibrated threshold is frozen into the NEW protocol version at
protocol-lock, before activation. No sequencing conflict: the data-driven
calibration uses data that precedes the current protocol's activation.

This resolves Codex's concern by separating v1 (conservative default, no data
dependency) from v2+ (prior-data calibration, available before activation).
The "natural gap" heuristic from my round-1 proposal is reframed as an
optional calibration procedure for subsequent protocol versions, not a
first-activation requirement.

Topic 018's versioned determinism rule
(`018/final-resolution.md:213-214`) is satisfied: same protocol version → same
threshold → same equivalence decisions. Different protocol versions may have
different thresholds because different protocols with different candidate
populations SHOULD have different equivalence boundaries. The threshold is
versioned WITH the protocol — changing it requires a new protocol version.

**Point 2: Structural granularity under-specified.** Codex argues that restating
"same descriptor hash + same parameter_family + same AST-hash subset" is just
the upstream pre-bucket contract, not a new granularity rule
(`codex/round-2_reviewer-reply.md:252-262`). Topic 008 warned that if 013
closes without specifying structural-hash granularity, the identity contract
remains semantically incomplete (`008/final-resolution.md:177-180`).

I concede this is under-specified. Topic 008 defined WHAT is hashed; 013's
obligation is to define the GRANULARITY — specifically, which parameter axes
are structural (part of the hash) vs. behavioral (deferred to nearest-rival
audit). The new rule:

A parameter axis is **structural** if changing it changes the strategy's
MECHANISM (entry/exit logic structure). A parameter axis is **behavioral** if
changing it only changes the strategy's TUNING (numeric values within a fixed
mechanism). The boundary:

- **Structural** (hashed): mechanism type (crossover vs breakout), indicator
  family (EMA vs SMA), exit type (trailing vs fixed), filter type (regime vs
  volatility). These change the AST structure — different operators, different
  control flow.
- **Behavioral** (not hashed): lookback windows, multipliers, thresholds within
  a fixed mechanism. These change parameter VALUES within the same AST
  structure.

This rule is not arbitrary — it is the natural boundary of Topic 008's
AST-hash field (`008/final-resolution.md:136-137`). If two candidates have the
same AST structure (same operators, same control flow), they have the same AST
hash regardless of parameter values. The granularity rule makes this explicit:
structural hash = AST hash captures mechanism-level identity, and individual
parameter values are the behavioral layer's responsibility.

The `parameter_family` field, which Codex correctly notes is already in the
pre-bucket contract, groups strategies by family membership (e.g.,
"momentum_crossover"). This is a COARSER grouping than AST hash — many
different AST structures can belong to the same parameter family. 013's
granularity rule says: within a parameter family, further structural
distinction is by AST hash. Within an AST-hash bucket, distinction is
behavioral (nearest-rival audit). This is the multi-level granularity that
Topic 008's warning asks for.

**Point 3: "Attempt all 5" overreaches.** Conceded. The "working minimum
inventory" (`018/final-resolution.md:127-136`) establishes that 5 proof
components exist in the framework. Whether every candidate undergoes all 5 is a
consumption rule. Topic 017 owns consumption rules
(`017/findings-under-review.md:433`: "Proof bundle consumption rules (what
constitutes 'passing' a proof component)").

013's remaining obligation regarding proof components: define the threshold
METHODOLOGY for each component — how each component's pass/fail boundary is
calibrated. This is architecturally distinct from:
- Consumption (which candidates undergo which components) → 017
- Proof-consumption rules (what constitutes "passing") → 017
- Completeness (how many components must be attempted) → 017

Topic 013 owns the threshold calibration procedure — HOW to determine the
boundary, not what happens when a candidate crosses it. Per
`018/final-resolution.md:173`: "Thresholds and proof-consumption rules:
017/013 own" — shared ownership split by: 013 = threshold methodology,
017 = consumption semantics.

**Point 4: N_min and absolute floors.** Codex argues that N_min and absolute
floor thresholds are numeric anomaly-threshold content that Topic 017 owns
(`codex/round-2_reviewer-reply.md:275-282`).

I accept that the specific absolute floor VALUES for each anomaly axis are
017's territory. However, the sparsity guard MECHANISM — the rule that switches
from population-relative to absolute thresholds below a population size — is
cross-cutting methodology that applies equally to ALL anomaly axes. It is a
property of the threshold methodology, not of any individual axis:

- **013 owns**: "when population size N < N_min, population-relative thresholds
  are statistically unreliable; switch to absolute floors." This is a
  methodological constraint on ALL threshold implementations.
- **017 owns**: the specific absolute floor value for each axis, N_min itself
  (as it determines the boundary of 017's per-axis value applicability), and
  the consumption semantics (what happens to anomalous candidates).

I acknowledge this boundary is debatable. If Codex insists that the entire
sparsity guard (including the existence of N_min) belongs to 017, I can accept
that — the architecturally important decision is that 013 SURFACES the
constraint that percentile-based thresholds fail in thin populations
(`codex/round-1_rebuttal.md:300-302`). Whether the remedy is owned by 013
(methodology) or 017 (axis-specific values) is a boundary question, not a
design question.

The essential content 013 contributes: the DIAGNOSIS that relative thresholds
are unreliable below some population size, and the REQUIREMENT that any
threshold methodology must account for this. 017 can own the specific remedy.

**Remaining dispute (narrowed)**: (a) whether conservative-default-at-lock +
prior-data-calibration-for-v2 resolves the sequencing conflict; (b) whether the
AST-hash-based mechanism/tuning boundary satisfies the granularity obligation;
(c) whether threshold methodology vs. consumption semantics correctly splits
013/017 ownership. `Open`.

---

## Cross-topic tensions (updated)

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 017 | ESP-01, ESP-04 | Coverage metrics overlap convergence measurement (CA-01). Novel candidate rate is 017's coverage signal, not 013's (conceded R2). Coverage exhaustion surfaces in HANDOFF dossier as separate artifact — does NOT veto 013's stop signal (corrected R3). | 013 owns convergence stop (Δρ + winner stability); 017 owns coverage signal. HANDOFF dossier consumes both separately. |
| 017 | ESP-04 | Proof-component consumption rules are 017's (conceded R2). Completion mandate ("attempt all 5") also 017's (conceded R3). 013 owns threshold methodology only. | 017 owns consumption + completion; 013 owns threshold calibration methodology. Shared per `018/final-resolution.md:173`. |
| 017 | ESP-04 | Anomaly threshold methodology (013 surfaces sparsity constraint) vs. axis-specific numeric values and N_min (017). 013 diagnoses the thin-population problem; 017 owns the specific remedy. | 013 contributes diagnostic constraint; 017 sets values. |
| 018 | SSE-09, SSE-04-THR | Routing confirmed. SSE-D-09 and SSE-D-04/05 provide binding interface constraints. | 013 implements within upstream-frozen interfaces. |
| 008 | SSE-04-IDV | 013's convergence hierarchy consumes 008's frozen identity vocabulary. Structural/behavioral boundary: AST hash captures mechanism-level identity; parameter values deferred to behavioral layer. | 008 owns structural pre-bucket fields; 013 specifies granularity rule (AST-hash = mechanism, nearest-rival = tuning). |
| 003 | F-05 | Correction law (013, field 5) interacts with test structure (003, stage transitions). BH at Stage 3 → more survivors → larger Stage 4 candidate set. Interaction documented; they are on different architectural axes (error rate philosophy vs test organization). | 013 owns correction law; 003 owns stage transition structure. |
| 001 | D-03, D-16 | Topic 001 deferred numeric convergence floors and session ceilings to 013. 013 specifies: three-signal stop framework, two-part convergence criterion, required protocol fields (M, ceiling). convergence_stall and CEILING_STOP are distinct signals (conceded R2) with distinct HANDOFF routing. | 013 produces both signals; 001 consumes via HANDOFF trigger vocabulary. |
| 007 | D-01 | `NO_ROBUST_IMPROVEMENT` as valid campaign exit depends on 013's convergence analysis being valid. | 007 provides constraint; 013 operationalizes via convergence stop + no robust candidate path. |

---

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-CA-01 | Convergence measurement framework | Thiếu sót | Open | Topic 013 should freeze mandatory multi-level reporting and a common comparison-domain contract, but should NOT freeze a canonical metric class (Spearman ρ) or significance test while the comparison domain remains unresolved — the metric's input is undecided, so the function cannot be validated. A significance-only τ definition does not satisfy Topic 001's substantive convergence floor obligation. | (1) The two-part criterion (significance + substantive τ_min floor) directly addresses the τ failure — it is no longer significance-only. (2) The metric CLASS (rank correlation) is a function; its desirable properties (continuous, closed-form, ordinal-preserving) hold regardless of which comparison domain is chosen — the function is validatable independent of input specification. (3) The comparison domain is within 013's own scope (SSE-04-THR), not a cross-topic dependency — both can be resolved in parallel. (4) No alternative metric has been proposed in 3 rounds; the burden is on the alternative. |
| X38-CA-02 | Stop conditions & diminishing returns | Thiếu sót | Open | Topic 013 should freeze a multi-signal stop framework with explicit separation between convergence stop and ceiling stop, but Δρ cannot safely absorb winner stability (K=10 swap counterexample), coverage stop should not give 017 a veto, and ranges/defaults must be evidence-backed rather than uncited folklore replacements. | (1) Winner stability is now an independent signal (conceded — counterexample conclusive). (2) Coverage is a dossier input, not a stop veto (conceded — 017 defines obligations, not blocks). (3) Three-signal framework with corrected ownership (Δρ + winner stability from 013, coverage from 017) restores the finding's original multi-signal design. (4) Numeric closure via required protocol fields with mandatory justification is specification (what to declare, why, how it integrates) not re-deferral — 013 cannot invent numbers unsupported by evidence, and folklore is what Topic 001 sent here to eliminate. |
| X38-SSE-09 | Scan-phase correction law default | Thiếu sót | Open | BH is not yet justified as default because false discoveries shape Stage 4 archive composition and probe neighborhoods before later cleanup — the "self-correcting" premise is overstated. Topic 003 still treats cascade as a live architectural option, and the correction law interacts with cascade structure. | (1) Self-correcting premise is conceded as overstated, but the ASYMMETRY survives: in sparse cells, false rejections (Holm risk) permanently empty cells with no downstream recovery, while false discoveries (BH risk) can still be caught by Stage 5-6 robustness tests — temporally bounded vs permanent. (2) In populated cells, false discoveries lose within-cell Stage 4 competition; false rejections mildly reduce diversity. The sparse-cell comparison is dispositive. (3) Cascade and correction law are on different architectural axes (test structure vs error rate philosophy); they interact but do not subsume each other. 013 owns field 5, 003 owns stage transitions, both document the interaction. |
| X38-SSE-04-THR | Equivalence + anomaly thresholds | Thiếu sót | Open | Conservative default at protocol-lock resolves the sequencing conflict for v1. But structural granularity must add value beyond restating 008's pre-bucket contract, the attempt-all mandate overreaches 017's consumption territory, and anomaly threshold numeric content (including N_min) belongs to 017. | (1) V1 conservative default at protocol-lock + v2 prior-data calibration (available before activation) resolves the sequencing concern without current-scan dependency. (2) The new granularity rule adds value: mechanism/tuning boundary (AST-hash = structural, parameter values = behavioral) specifies the multi-level granularity Topic 008 warned about. (3) Attempt-all is conceded to 017. (4) Axis-specific floor values are conceded to 017. 013 contributes the diagnostic constraint (thin populations break percentile thresholds) and the requirement that any threshold methodology must account for it — the specific remedy can be 017's. |
