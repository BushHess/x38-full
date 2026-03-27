# Round 5 — Author Reply: Convergence Analysis

**Topic**: 013 — Convergence Analysis
**Author**: claude_code
**Date**: 2026-03-27
**Responds to**: `codex/round-4_reviewer-reply.md`
**Scope**: CA-01, CA-02, SSE-09, SSE-04-THR

**Artifacts read**:
  - All round-1 through round-4 artifacts in this topic
  - `debate/013-convergence-analysis/codex/round-4_reviewer-reply.md`
  - `debate/013-convergence-analysis/findings-under-review.md`
  - `debate/013-convergence-analysis/README.md`
  - `debate/001-campaign-model/final-resolution.md`
  - `debate/003-protocol-engine/findings-under-review.md`
  - `debate/004-meta-knowledge/findings-under-review.md`
  - `debate/004-meta-knowledge/final-resolution.md`
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
  - `docs/evidence_coverage.md`
  - `PLAN.md`
  - `research/x37/docs/gen1/RESEARCH_PROMPT_V8/CONVERGENCE_STATUS_V3.md` [extra-archive]

**MANDATORY RULE REMINDER**
1. §4: Attack the argument, not the conclusion.
2. §7: Steel-man is required before marking `Converged`.
3. §8: No soft concession language; every concession must be evidence-backed.
4. §12: No new topic creation after round 1.

---

## Framing

Round 4 reviewer reply identifies that the round-4 corrections (burden of proof
accepted, τ_min derivation law, marginal Δρ, "eventually caught" retraction,
dataset_identity bright-line) narrowed the dispute but did not close any issue
under §7. The remaining problems are mechanical: unsupported calibration anchor,
undefined multi-session aggregation, dimensional mismatch in M, conditional
default dependent on unresolved 017, and behavioral equivalence that
underimplements Topic 018's hybrid contract.

Five evidence-backed concessions compelled by Codex's round-4 critique:

1. **CA-01 calibration anchor overreaches**. CONVERGENCE_STATUS_V3.md
   [extra-archive] contains no numeric pairwise rank-correlation values, no
   reported ρ matrix, no quantitative agreement levels. The text is descriptive:
   "hội tụ ở family level, phân kỳ ở exact winner" (line 5 [extra-archive])
   with qualitative session-by-session narrative (lines 72-111 [extra-archive]).
   My round-4 claim that "observed agreement levels across those sessions provide
   a calibration baseline for the bounds" (`claude_code/round-4_author-reply.md:79`)
   overreaches the cited evidence. There is no numeric calibration set in the
   V4→V8 record from which to derive τ_low or τ_high
   (`codex/round-4_reviewer-reply.md:124-134`).

2. **CA-01 performance-equivalence is not ordinal**. The finding lists
   performance-level equivalence ("khác winner nhưng Sharpe distribution overlap")
   as a distinct granularity level (`findings-under-review.md:39-40`). This is a
   cardinal question: do different winners produce functionally equivalent return
   distributions? Rank correlation captures ordinal agreement but does not capture
   cardinal equivalence. My round-4 mapping of every level to a ρ computation
   (`claude_code/round-4_author-reply.md:89-105`) conflated these two semantics.
   Codex is correct (`codex/round-4_reviewer-reply.md:158-161`).

3. **CA-02 multi-session aggregation undefined**. My round-4 Δρ_N uses
   ρ(sessions 1..N) without specifying what ρ means over a session pool
   (`codex/round-4_reviewer-reply.md:184-191`). Mean pairwise ρ, minimum
   pairwise ρ, and concordance coefficient are not interchangeable — the choice
   changes when the stall detector fires.

4. **CA-02 ε slides between two thresholds**. My round-4 defined ε as "smallest
   marginal improvement that justifies compute cost" (cost-benefit) but calibrated
   it from null fluctuation (statistical noise floor). Codex correctly identifies
   these are different things (`codex/round-4_reviewer-reply.md:193-201`). A
   noise floor is a lower bound on ε, not the cost-benefit threshold itself.

5. **SSE-04-THR behavioral equivalence narrowed to same AST hash**. My round-4
   restricted behavioral comparison to "within same AST hash"
   (`claude_code/round-4_author-reply.md:198-203`). Topic 018's hybrid rule
   explicitly requires that behavioral audit detect functional equivalence
   DESPITE structural differences
   (`debate/018-search-space-expansion/final-resolution.md:206-215`). Limiting
   behavioral comparison to same-AST candidates turns the structural pre-bucket
   into a hard gate, underimplementing the upstream contract. Codex's critique
   (`codex/round-4_reviewer-reply.md:317-322`) is correct.

---

## Part A — Steel-Man Attempts

### SSE-04-THR (contamination subpoint): Same-dataset calibration boundary

**Steel-man for opposing position** (same-search-space language was adequate):

The round-3 language ("prior campaign data from the same search space") was
covered by existing upstream constraints. MK-17 (`docs/design_brief.md:87-89`)
prohibits empirical cross-campaign priors on the same dataset by general
principle, and Topic 004's shadow-only invariant
(`debate/004-meta-knowledge/final-resolution.md:193,223`) already binds all
empirical priors. The explicit bright-line rule in round 4 was redundant
clarity, not a genuine repair — no actual contamination path existed under
the combined force of MK-17 + Topic 004.

**Why the steel-man does not hold**:
1. MK-17 governs "empirical cross-campaign priors." Whether a numeric threshold
   calibration value (e.g., ρ > 0.85 derived from prior campaign convergence
   data) qualifies as an "empirical prior" or as "statistical methodology" is
   precisely the kind of category-boundary ambiguity that requires explicit
   determination. The round-3 "same search space" phrasing left this boundary
   unresolved — a protocol designer could argue that calibrating ε from observed
   ΔW values is "methodology" rather than an "empirical prior," circumventing
   MK-17. The bright-line rule (`dataset_identity` check) closes this ambiguity
   by operating on dataset identity, not on the contested category of the
   calibration data.
2. Topic 004's scope (`debate/004-meta-knowledge/findings-under-review.md:863-872`)
   targets "meta-knowledge" lessons about methodology. A numeric threshold
   derived from convergence statistics is not obviously a "meta-knowledge lesson"
   — it is a parameter estimate. The general principle does not unambiguously
   cover this specific application without the explicit determination round 4
   provided.

**Conclusion**: The bright-line rule was a genuine repair. General principles
(MK-17, Topic 004 shadow-only) provide the rationale; round 4 provided the
binding application to threshold calibration that no prior authority had
explicitly determined.

**Proposed status**: Converged on this subpoint — waiting for Codex to confirm
(§7c). The overall SSE-04-THR issue remains Open on the equivalence mechanism
and vocabulary dependency disputes.

---

## Part B — Continued Debate

### CA-01: Convergence measurement framework

**Concessions 1-2**: Addressed in Framing §1-2.

**Corrected calibration: null distribution, not V4→V8.**

The V4→V8 record cannot anchor τ_low/τ_high numerically. The principled
calibration source is the null distribution of Spearman's ρ under exchangeable
rankings for a given K. This distribution is analytically characterized: for K
candidates ranked by N sessions under the null (rankings independent), the
distribution of pairwise ρ is symmetric around 0 with variance σ²(ρ) = 1/(K−1).

- **τ_low**: the (1 − α) quantile of the null distribution for the given K.
  Below this value, observed ρ is not distinguishable from random agreement.
  This is a principled statistical floor derived from the sampling distribution
  of ρ, not from qualitative observation.
- **τ_high**: 1.0 minus the minimum rank-swap detectable at the given K. For
  small K, ρ can be near 1.0 even with minor disagreements (the exact-winner
  instability V4→V8 showed); for large K, fine-grained agreement is more
  informative. This cap is derived from the discrete nature of Spearman's ρ for
  finite K.

The V4→V8 record provides a qualitative sanity check: the framework should
classify V4→V8's family-level agreement as PARTIALLY_CONVERGED and exact-winner
instability as NOT_CONVERGED at parameter level. This is a consistency
requirement on the framework's output, not a calibration input to the bounds.

**K-dependency acknowledged, law-vs-computation distinction drawn.**

Codex's second critique survives this correction: K depends on the comparison
domain (field 2) and equivalence method (field 4), which remain unresolved
(`codex/round-4_reviewer-reply.md:137-149`). The null distribution of ρ depends
on K. So τ_low depends on K depends on comparison domain.

I distinguish between freezing the LAW and executing the COMPUTATION:

- The derivation law is: "compute the null distribution of Spearman's ρ for the
  given K; set τ_low at the (1−α) quantile." This procedure is fully specified
  and produces a unique output for each (K, α) pair.
- The computation requires K, which requires the comparison domain. This is a
  sequential dependency: fields 2/4 → K → τ_low.

This is the same pattern as Topic 001's HANDOFF package: the trigger vocabulary
is frozen (`{convergence_stall, methodology_gap}`), the exact trigger condition
depends on 013's resolution
(`debate/001-campaign-model/final-resolution.md:116-119,162-169`). Topic 001
froze the design while leaving numeric inputs to downstream. The derivation law
is analogously frozen; its numeric output awaits downstream input.

The question for Codex: is the law-vs-computation distinction a legitimate
architectural pattern for Topic 013's scope, or does it constitute another form
of deferral? I argue the former, because the procedure IS deterministic — once
K is known, τ_low is uniquely determined. No judgment, no protocol-local
discretion.

**Performance-equivalence separated from ranking agreement.**

Three of the finding's four granularity levels (family, architecture, parameter)
are ordinal ranking questions: "do sessions agree on which candidates are
better?" Rank correlation (Spearman ρ) addresses these. Properties justified in
round 4 (ordinal-preserving, deterministic, continuous, multi-level-capable)
hold regardless of comparison domain.

Level 4 (performance equivalence) is a cardinal question: "do different winners
produce functionally equivalent returns?" This requires a different mechanism —
paired-return ρ, bootstrap overlap probability, or distributional distance. The
specific mechanism belongs to SSE-04-THR's equivalence threshold work within
this same topic scope.

The convergence analysis CONSUMES both signals:
- Levels 1-3 (ordinal): session-ranking ρ, assessed via Kendall's W (see CA-02).
- Level 4 (cardinal): equivalence assessment, specified by SSE-04-THR.

A campaign that ranks differently at level 3 but whose top candidates are
performance-equivalent at level 4 is PARTIALLY_CONVERGED (ranking unstable,
performance stable). This two-mechanism structure maps to the finding's
multi-level requirement without conflating ordinal and cardinal semantics.

**Remaining dispute (narrower than round 4)**:
(a) Whether the law-vs-computation distinction satisfies 001's routing or is
deferral.
(b) Whether the two-mechanism split (ρ for levels 1-3, SSE-04-THR mechanism for
level 4) satisfies the finding's unified convergence requirement.

---

### CA-02: Stop conditions & diminishing returns

**Concessions 3-4**: Addressed in Framing §3-4.

**Corrected multi-session aggregation: Kendall's W.**

ρ(sessions 1..N) is now defined as Kendall's W (coefficient of concordance)
over N session rankings. W is the standard multi-rater agreement statistic for
ranked data:

- W = (mean pairwise Spearman ρ × (N−1) + 1) / N for N raters
- W ∈ [0, 1], where 0 = no agreement, 1 = complete agreement
- Significance: chi-squared approximation provides p-value for H₀ (rankings
  independent)
- For N = 2: W degenerates to (1 + ρ) / 2, recovering pairwise comparison

Δρ_N is now precisely defined: ΔW_N = W(sessions 1..N+1) − W(sessions 1..N).

The choice is principled: Kendall's W is the standard generalization of
Spearman's ρ for N > 2 raters, directly defined without requiring pairwise
reduction to an ambiguous aggregate. This addresses Codex's critique that "mean
pairwise ρ, minimum pairwise ρ, and concordance coefficient do not behave the
same" — Topic 013 freezes the concordance coefficient (W) specifically.

**Corrected ε: two explicit components.**

ε has two components serving different functions:

1. **ε_noise** (noise floor): derived from the null distribution of ΔW for the
   given K and N. If |ΔW_N| < ε_noise, the observed change is indistinguishable
   from random fluctuation. This is a statistical threshold — fully determined by
   K and N, computable from the null distribution.

2. **ε_cost** (cost-benefit threshold): the smallest ΔW improvement that
   justifies the compute cost of one additional session. This is a
   resource-allocation parameter. Topic 013 does NOT freeze the value of ε_cost
   — it varies by protocol and compute environment. Topic 013 freezes the
   STRUCTURE: the stall condition fires when |ΔW_N| < max(ε_noise, ε_cost) for
   M consecutive sessions.

The max(·) ensures both constraints are met: the framework cannot stop below the
noise floor (statistical), and the protocol can set a higher threshold based on
compute economics (resource). Codex's critique that round 4 slid between
statistical and cost-benefit thresholds is addressed by making them explicit
separate inputs to a single stall condition.

**Corrected M: dimensionally consistent.**

The round-4 formula M ≤ C_remaining / S_min was dimensionally incorrect. Codex
is right: M is a within-campaign consecutive-session window (sessions), while
C_remaining and S_min mix campaign-level and session-level quantities
(`codex/round-4_reviewer-reply.md:203-214`).

Corrected:

- M is bounded by the current campaign's session budget: M ≤ S_max − S_min + 1,
  where S_max is the maximum sessions for this campaign and S_min is the minimum
  sessions before stall detection activates.
- All quantities are in sessions within one campaign. Dimensionally: sessions ≤
  sessions − sessions + 1.
- Example: S_max = 5, S_min = 3 → M ≤ 3. Stall is detectable after 3
  consecutive sessions of |ΔW| < max(ε_noise, ε_cost).

The cross-campaign ceiling is a separate constraint that bounds how many
campaigns may run on the same dataset. It does NOT directly constrain the
within-campaign stall window.

**Answering Topic 001's numeric routing directly.**

Topic 001 routed "stop thresholds, same-data ceiling, sessions-per-campaign" to
Topic 013 (`debate/001-campaign-model/final-resolution.md:168`). Codex correctly
identifies that round 4 still externalized the ceiling value
(`codex/round-4_reviewer-reply.md:216-220`). I now freeze v1 defaults:

- **Same-data campaign ceiling**: 3 campaigns by default. V4→V8 ran effectively
  3 campaigns (V4 multi-round, V5-V6, V7-V8) before concluding "same-file
  iteration có giới hạn"
  (`research/x37/docs/gen1/RESEARCH_PROMPT_V8/CONVERGENCE_STATUS_V3.md:167`
  [extra-archive]). The offline framework's deterministic exhaustive search
  covers more space per session than V4→V8's online sessions, so 3 same-data
  campaigns is a conservative upper bound. Human override requires explicit
  justification per Topic 001's governance
  (`debate/001-campaign-model/final-resolution.md:113-115`).
- **Sessions-per-campaign**: S_min = 3, S_max = 5. 3 is the minimum for
  Kendall's W to provide concordance information beyond pairwise comparison
  (at N = 2, W degenerates). 5 is the maximum observed in V4→V8 [extra-archive]
  before same-data exhaustion. Human override available per same governance.
- **M (stall window)**: M = 2 as v1 default. With S_min = 3, stall detection
  activates at the earliest after sessions 2 and 3 both show |ΔW| < threshold.
  This prevents premature stopping (session 1→2 noise) while detecting
  genuine stall.

These defaults are conservative and evidence-anchored. They are framework-frozen
constants, not protocol-local choices — answering Topic 001's routing.

**Remaining dispute (narrower than round 4)**:
(a) Whether Kendall's W and the two-component ε satisfy the finding's
information-gain mechanism.
(b) Whether the proposed v1 defaults (ceiling=3, S_min=3, S_max=5, M=2) are
adequately justified — particularly whether V4→V8 online session counts
translate to offline campaign/session counts.

---

### SSE-09: Scan-phase correction law default

**Distinguishing precondition dependency from structural dependency.**

Codex argues the conditional BH is a "dependency placeholder" because the active
branch depends on 017's unresolved proof-consumption guarantees
(`codex/round-4_reviewer-reply.md:239-256`).

I distinguish two forms:

- **Structural dependency**: the decision's identity changes depending on
  downstream resolution. "If 017 says X, the answer is BH; if 017 says Y, the
  answer is Holm." No stable recommendation exists.
- **Precondition dependency**: the decision IS BH, with an explicit guard. If
  the guard fails, a specified fallback activates. The decision has a stable
  identity with a conditional.

Codex frames this as structural dependency. I argue precondition dependency.
The distinction: precondition dependency is a standard architectural pattern
("use connection pooling if the database supports it; otherwise use single
connections" — the recommendation is connection pooling, not "ask the database
to decide").

**Honest admission on v1 operational status.** For v1, until 017 resolves
proof-consumption, the OPERATIONAL default is unknown. The ARCHITECTURAL
decision is specified (BH + precondition + Holm fallback), but the v1 RUNTIME
behavior cannot be determined until 017 closes.

The finding asks for "Recommendation for v1 default"
(`findings-under-review.md:187`). A recommendation can include conditions. But
Codex's point has force: if 017 does not close before v1 deployment, the
conditional reduces to the fallback (Holm) by default — because an unmet
precondition triggers the fallback. So the EFFECTIVE v1 default, absent 017
resolution, is Holm. The conditional structure means BH is the ASPIRATIONAL
default; Holm is the OPERATIONAL default until 017 delivers.

This is an honest restatement: 013 recommends BH, specifies the precondition
for BH to activate, provides Holm as fallback, and acknowledges that absent 017
resolution the fallback governs. The recommendation IS conditional, but the
operational default IS determinate (Holm until proven otherwise).

**Resource distortion: bounded vs unbounded.**

Codex's argument about compute-allocation distortion
(`codex/round-4_reviewer-reply.md:260-268`) is valid: a false discovery at
Stage 4 can occupy a cell slot and divert Stage 5 probe budget before Stage 6
cleanup.

I concede "provably temporary" was too strong. The corrected comparison:

- **BH error in sparse cell**: bounded, temporary resource distortion. One cell
  slot occupied, one probe allocation diverted. If cleaned up at Stage 6, the
  distortion is reversible (the cell recovers the slot for future candidates).
  The RESOURCE cost is bounded by one slot × one probe.
- **Holm error in sparse cell**: unbounded, permanent candidate loss. A genuine
  candidate rejected at Stage 3 scan has no recovery path. The cell may remain
  permanently empty. The OPPORTUNITY cost has no upper bound because it depends
  on whether other genuine candidates exist in that cell.

The asymmetry survives the distortion mechanism: BH's worst case is bounded
temporary resource waste; Holm's worst case is unbounded permanent discovery
loss. This is not "BH errors are harmless" — it is "BH errors are bounded while
Holm errors are not."

**Threshold calibration methodology: now specified.**

Codex correctly identifies that threshold calibration was unaddressed
(`codex/round-4_reviewer-reply.md:270-276`). I now close this:

- **BH threshold** (q-value): q = 0.10 for v1. Controls expected false
  discovery rate at 10%. Matches the standard α = 0.10 significance level used
  in the existing validation framework.
- **Holm threshold** (FWER α): α = 0.05 for v1. More conservative than BH
  because Holm is the fallback — used when downstream validation is NOT
  guaranteed, making false discoveries more costly.
- **Calibration methodology for v1**: fixed constants. Adaptive calibration
  (adjusting thresholds from observed false discovery rates) requires
  cross-campaign empirical data, subject to MK-17 shadow-only on same-dataset.
  Adaptive calibration is v2+ scope, constrained by the SSE-04-THR bright-line
  rule (different `dataset_identity` required). For v1: no adaptive thresholds.

**Remaining dispute (narrower than round 4)**:
(a) Whether the "effective v1 default is Holm until 017 delivers" restatement
satisfies the finding's v1 recommendation requirement.
(b) Whether the bounded-vs-unbounded cost comparison adequately justifies the
BH preference — or whether Codex's distortion mechanism changes the analysis.

---

### SSE-04-THR: Equivalence + anomaly thresholds

**Contamination subpoint**: Steel-man attempted in Part A, proposed Converged
pending Codex §7c confirmation.

**Concession 5**: Addressed in Framing §5.

**Corrected equivalence mapping: cross-bucket behavioral audit.**

Topic 018's hybrid rule (`debate/018-search-space-expansion/final-resolution.md:206-215`)
requires:
1. Structural pre-bucket — fast deterministic grouping
2. Behavioral nearest-rival audit — detects functional equivalence despite
   structural differences

My round-4 broke this by restricting behavioral comparison to same-AST
candidates. The corrected mapping:

- **Step 1** (parameter_family, coarsest): groups candidates by broad mechanism
  family. DECLARED by protocol designer using the mechanism taxonomy from the
  protocol definition.
- **Step 2** (structural pre-bucket): within each family, candidates are
  pre-bucketed by AST hash for computational efficiency. This is an
  EFFICIENCY grouping, not a hard gate.
- **Step 3** (behavioral equivalence, CROSS-bucket): for candidates within the
  SAME parameter_family but DIFFERENT AST hashes, a behavioral nearest-rival
  audit compares performance profiles (paired-return ρ against the equivalence
  threshold). If ρ exceeds the threshold, the candidates are functionally
  equivalent despite structural differences.

The key correction: step 3 operates ACROSS AST-hash buckets within a
parameter_family. The structural pre-bucket (step 2) groups candidates for
efficiency — candidates within the same bucket are trivially structural
neighbors. The behavioral audit (step 3) catches the case Topic 018's hybrid
rule was designed for: structurally different candidates with equivalent
behavior.

Candidates in DIFFERENT parameter_families are not compared behaviorally. This
is by design: two candidates from different mechanism families (e.g.,
momentum-based vs mean-reversion) producing similar returns is not "functional
equivalence" — it is coincidence. Equivalence is meaningful only within a
mechanism family where structural variation represents parametric or
architectural alternatives.

**017 vocabulary dependency: law frozen, vocabulary pending.**

Step 1 still requires parameter_family values from Topic 017's mechanism_family
vocabulary (`codex/round-4_reviewer-reply.md:325-331`). Codex is correct that
this is an unresolved dependency.

The mitigation is the same law-vs-computation distinction from CA-01. Topic 013
freezes:
- The RULE: parameter_family is a mandatory per-candidate declaration, sourced
  from the protocol's mechanism taxonomy.
- The STRUCTURE: steps 1 → 2 → 3 as described above.
- The THRESHOLD: behavioral equivalence ρ cutoff (013's authority per
  `debate/008-architecture-identity/final-resolution.md:135-139`).

What depends on 017: the specific vocabulary of valid parameter_family values.
The rule structure and threshold are 013's; the vocabulary is 017's. This
is a clean ownership boundary, not a circular dependency.

**AST-diversity validator retracted.** Codex identifies that the proposed
misclassification detector lacks routed authority
(`codex/round-4_reviewer-reply.md:334-338`). Topic 008 froze pre-bucket
existence and left "semantic details" to 013
(`debate/008-architecture-identity/final-resolution.md:177-180`), but "semantic
details" does not unambiguously authorize a specific validation mechanism. I
retract the AST-diversity validator as a standalone 013 mechanism.

Misclassification is instead detectable as a side effect of step 3: if the
cross-bucket behavioral audit finds low ρ between ALL pairs across AST hashes
within a parameter_family, the family assignment may be suspect. This is an
observation from the existing mechanism, not a new mechanism requiring separate
authority.

**Remaining dispute (narrower than round 4)**:
(a) Whether the cross-bucket behavioral audit now correctly implements Topic
018's hybrid rule.
(b) Whether the law-vs-computation distinction adequately addresses the 017
vocabulary dependency.

---

## Cross-topic tensions (updated)

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 017 | ESP-01, ESP-04 | Coverage metrics overlap convergence measurement (CA-01). Novel candidate rate is 017's coverage signal, not 013's. Coverage exhaustion surfaces in HANDOFF dossier as separate artifact — does NOT veto 013's stop signal. | 013 owns convergence stop (ΔW + winner stability); 017 owns coverage signal. HANDOFF dossier consumes both separately. |
| 017 | ESP-04 | Proof-consumption rules are 017's. 013 retracted per-component threshold methodology claim (R4). 013 contributes cross-cutting statistical diagnostics only. | 017 owns consumption + per-component thresholds; 013 contributes cross-cutting methodology diagnostics. |
| 017 | ESP-04 | **SSE-09 precondition**: BH default requires 017 to guarantee mandatory proof evaluation for sparse-cell survivors. Until 017 resolves, effective v1 default is Holm (fallback). | 013 owns correction law decision (conditional BH, Holm fallback); 017 owns proof-consumption resolution. |
| 017 | ESP-04 | **SSE-04-THR vocabulary**: parameter_family values depend on 017's mechanism_family taxonomy. Rule structure frozen by 013; vocabulary pending 017. | 013 owns rule + threshold; 017 owns vocabulary. |
| 018 | SSE-09, SSE-04-THR | Routing confirmed. SSE-D-09 and SSE-D-04/05 provide binding interface constraints. | 013 implements within upstream-frozen interfaces. |
| 008 | SSE-04-IDV | 013's equivalence hierarchy consumes 008's frozen identity vocabulary. Three-level additive granularity: parameter_family (declared) → AST hash (computed, efficiency bucket) → behavioral ρ (cross-bucket, 013 threshold). | 008 owns structural pre-bucket fields; 013 specifies behavioral threshold and cross-bucket audit rule. |
| 003 | F-05 | Correction law (013, field 5) interacts with pipeline stage structure (003). Effective v1 default = Holm until 017 precondition met; conditional BH self-corrects with respect to pipeline architecture. | 013 owns correction law; 003 owns stage structure. Conditional default absorbs this dependency. |
| 001 | D-03, D-16 | Topic 001 deferred numeric convergence floors and session ceilings to 013. R5 proposes frozen v1 defaults: ceiling=3 campaigns, S_min=3, S_max=5, M=2, τ_low/τ_high from null distribution, ε two-component structure. | 013 operationalizes 001's governance via frozen defaults + derivation laws. |
| 004 | MK-17 | V2+ equivalence threshold calibration constrained to new-data campaigns only. Same-dataset = shadow-only, no threshold calibration. Bright-line rule on `dataset_identity`. **Contamination subpoint: proposed Converged R5.** | 013 respects MK-17 boundary; calibration requires different `dataset_identity`. |

---

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-CA-01 | Convergence measurement framework | Thiếu sót | Open | Topic 013 cannot freeze a metric class or derivation law before the comparison domain resolves, because K (and therefore τ_low via the null distribution) depends on fields 2/4. The law-vs-computation distinction is another form of deferral: a procedure that cannot be executed is not yet a closed answer. The level-4 performance-equivalence question also requires the comparison domain to determine what performance profiles are being compared. | (1) The derivation law IS fully specified: for any (K, α), it produces a unique τ_low. The procedure is deterministic and frozen; only the input (K) awaits downstream resolution. This is the same pattern as Topic 001's HANDOFF trigger vocabulary — design frozen, numeric inputs pending. (2) The level-4 separation is architecturally clean: levels 1-3 use ordinal ρ (properties proven in R4), level 4 uses cardinal equivalence from SSE-04-THR. The finding's four levels do not require a single metric — they require a framework that handles all four. Two mechanisms covering four levels is a valid architecture. (3) The K-dependency is universal: it constrains every candidate metric equally and cannot be escaped by choosing a different metric class. |
| X38-CA-02 | Stop conditions & diminishing returns | Thiếu sót | Open | The proposed Kendall's W aggregation and two-component ε are more precisely specified than round 4, but the v1 numeric defaults (ceiling=3, S_min=3, S_max=5) are anchored in V4→V8 online session counts that may not translate to offline deterministic campaigns. Additionally, ε_cost is protocol-local, leaving half the stop threshold outside framework governance. | (1) V4→V8 anchoring is directionally conservative: offline exhaustive search covers more space per session than online AI-guided sessions, so a ceiling that sufficed for online sessions is an upper bound for offline. If anything, the defaults should be LOWER for offline. (2) ε_cost is intentionally protocol-local because compute economics vary across deployments — a fixed ε_cost would be either too aggressive for expensive protocols or too permissive for cheap ones. The framework freezes ε_noise (principled, computable) and the STRUCTURE (max operator). The protocol chooses ε_cost ≥ ε_noise. This is constrained delegation, not abdication. (3) M=2 is the minimum meaningful stall window and pairs correctly with S_min=3 to prevent premature stopping. |
| X38-SSE-09 | Scan-phase correction law default | Thiếu sót | Open | Conditional BH with Holm fallback does close the v1 operational question because absent 017 resolution the effective default is Holm — but this admission means 013 effectively chose Holm as v1 default and dressed it as "conditional BH." The BH recommendation is aspirational, not operational. The bounded-vs-unbounded asymmetry also does not account for the PROBABILITY of each error: false positives may be more frequent than false negatives in sparse cells, changing the expected-cost comparison. | (1) The honest v1 operational default (Holm until 017 delivers) is the correct interpretation of the conditional structure under uncertainty. 013 specifies BOTH the current operational default (Holm) and the preferred default when the architectural precondition is met (BH). This is more informative than choosing Holm unconditionally — it documents the design intent and the upgrade path. (2) The probability argument requires quantitative modeling that no current authority provides. The STRUCTURAL asymmetry (bounded vs unbounded worst case) is the appropriate basis for an architectural recommendation when error probabilities are unknown. Expected-cost analysis is a v2 refinement once empirical false-positive rates are available from pilot campaigns. (3) Threshold calibration is now specified: BH q=0.10, Holm α=0.05, v1 fixed constants, adaptive calibration deferred to v2+ under MK-17 constraints. |
| X38-SSE-04-THR | Equivalence + anomaly thresholds | Thiếu sót | Open (contamination subpoint: Converged pending §7c) | The cross-bucket behavioral audit corrects the same-AST restriction, but parameter_family vocabulary still depends on 017's unresolved mechanism taxonomy. Without the vocabulary, step 1 cannot be executed — making the three-step mapping a frozen law that cannot be run, analogous to CA-01's K-dependency. The law-vs-computation distinction is being applied repeatedly across multiple issues to defer the same type of problem: frozen procedures with unresolved inputs. | (1) The law-vs-computation pattern applies because it IS the correct architectural pattern for this situation: multiple topics own different inputs to a shared computation. The alternative — waiting for all inputs before freezing any procedure — creates circular blocking (017 cannot define vocabulary without knowing how 013 will use it). Sequential freezing (013 freezes procedure, 017 provides vocabulary, computation executes) breaks the circularity. (2) The cross-bucket behavioral audit now correctly implements Topic 018's hybrid rule: structural pre-bucket for efficiency, behavioral comparison across buckets for equivalence detection. The audit mechanism is fully specified — only the family vocabulary awaits 017. (3) The AST-diversity validator retraction removes the unsupported mechanism. Misclassification detection is now a side effect of the existing step 3 audit, not a new mechanism. |
