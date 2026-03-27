# Round 1 — Opening Critique: Convergence Analysis

**Topic**: 013-convergence-analysis
**Author**: claude_code
**Date**: 2026-03-27
**Scope**: CA-01 (Convergence measurement framework),
           CA-02 (Stop conditions & diminishing returns),
           SSE-09 (Scan-phase correction law default),
           SSE-04-THR (Equivalence + anomaly thresholds)
**Input documents**:
  - `research/x38/AGENTS.md`
  - `research/x38/x38_RULES.md`
  - `research/x38/docs/online_vs_offline.md`
  - `research/x38/docs/design_brief.md`
  - `research/x38/PLAN.md`
  - `research/x38/debate/rules.md`
  - `research/x38/debate/prompt_template.md`
  - `research/x38/debate/debate-index.md`
  - `research/x38/debate/013-convergence-analysis/README.md`
  - `research/x38/debate/013-convergence-analysis/findings-under-review.md`
  - `research/x38/debate/001-campaign-model/final-resolution.md`
  - `research/x38/debate/007-philosophy-mission/final-resolution.md`
  - `research/x38/debate/008-architecture-identity/final-resolution.md`
  - `research/x38/debate/018-search-space-expansion/final-resolution.md`
  - `research/x38/debate/018-search-space-expansion/findings-under-review.md`
  - `research/x38/debate/018-search-space-expansion/README.md`

---

## Preamble

I write as architect opening the debate for Topic 013 (Convergence Analysis).
This topic addresses the mathematical and statistical core that determines when
a campaign has produced a defensible answer — or should stop trying. Without a
rigorous convergence algorithm, the Campaign → Session model (frozen in
Topic 001) is structurally complete but operationally hollow: the framework
knows *what* a campaign is, but not *when it has concluded*.

Per `debate/rules.md` §5, the burden of proof lies with whoever proposes
changing the current design. The current design (`design_brief.md:96-118`,
`PLAN.md:445-510`) mentions convergence analysis as a campaign component but
provides no algorithm. The findings (F-30, F-31) correctly classify this as
Thiếu sót — the gap is real and must be filled. My burden as critic is to
evaluate whether the proposed framework elements are architecturally sound and
complete, not whether convergence analysis is needed (that is established).

Topic 013 has 4 findings: 2 original (CA-01, CA-02) and 2 routed from Topic 018
(SSE-09, SSE-04-THR). The routed issues carry binding architectural context from
Topic 018's closure (CLOSED 2026-03-27, standard 2-agent debate, 10 Converged +
1 Judgment call). Specifically, SSE-D-09 (multiplicity control coupling via
SSE-D-04 field 5) and SSE-D-04/05 (equivalence thresholds + anomaly axes)
established the *obligation* for Topic 013 to specify values; the *interface*
is frozen upstream. I debate each finding independently, but the routed issues
are architecturally constrained by their upstream decisions.

The upstream dependency chain is fully resolved: Topic 007 (philosophy, CLOSED
2026-03-23) froze the 3-tier claim model and `NO_ROBUST_IMPROVEMENT` as valid
output. Topic 001 (campaign model, CLOSED 2026-03-23) froze campaign properties,
HANDOFF law, and explicitly deferred numeric convergence floors to Topic 013
(`final-resolution.md:168`). Topic 008 (architecture identity, CLOSED 2026-03-27)
froze the candidate-level identity vocabulary (SSE-04-IDV) with ownership split:
008 interface + structural pre-bucket, 013 semantics, 017 consumption. All
upstream gates are clear.

---

## CA-01: Convergence measurement framework — ACCEPT with amendments

### Position

The finding correctly identifies a critical gap: `design_brief.md` and F-03
mention "convergence analysis" but provide no algorithm. The V4→V8 evidence
(`CONVERGENCE_STATUS_V3.md` [extra-archive]) demonstrates the problem
empirically: 5 sessions produced 5 different family-level winners, and the
conclusion "hội tụ ở family level, phân kỳ ở exact winner" was reached by
human judgment, not metric. An offline framework that promises deterministic
reproducibility (`docs/online_vs_offline.md:12-25`) cannot rely on human
judgment for its core convergence determination.

**Key argument**: The finding's 4-part structure (granularity, distance metric,
statistical test, multi-level convergence) is the correct decomposition. I
accept this structure and propose amendments to narrow the design space for
each component.

**On granularity**: The finding proposes 4 levels (family, architecture,
parameter, performance). I argue the framework should measure ALL levels but
report convergence as a **hierarchical verdict** — convergence at a coarser
level (family) is meaningful even without convergence at finer levels (parameter).
This matches the V4→V8 empirical record: "D1 slow" family convergence was a real
signal even though exact winners diverged. The hierarchical model should be:

```
FULLY_CONVERGED     := family + architecture + parameter converged
STRUCTURALLY_CONVERGED := family + architecture converged, parameter divergent
FAMILY_CONVERGED    := family converged, architecture/parameter divergent
NOT_CONVERGED       := family divergent
```

This is strictly more informative than the finding's 3-level model
(FULLY/PARTIALLY/NOT) because it distinguishes between two qualitatively
different "partial" states: structural convergence (same architecture, different
parameters — likely plateau/flat-optimum evidence) vs family-only convergence
(different architectures within same family — weaker signal).

**Evidence**: Topic 001 Decision 1 (D-03) froze campaign properties including
convergence analysis but deferred "exact numeric floors to Topic 013"
(`001-campaign-model/final-resolution.md:47`). The hierarchical verdict is the
semantic framework those numeric floors operate on. Topic 007 Decision 3 (D-22)
froze 3 evidence types including "deterministic convergence (same-archive)" —
the convergence verdict feeds this evidence type directly.

**On distance metrics**: The finding lists 4 candidate metrics. I argue the
framework should specify a **primary metric** for the convergence verdict and
allow **auxiliary metrics** for diagnostics. The primary metric should be
**rank correlation (Spearman ρ)** across session top-K rankings, for three
reasons:

1. *Determinism*: Spearman ρ is a closed-form computation on session outputs,
   requiring no resampling. This satisfies the offline paradigm's
   reproducibility requirement.
2. *Robustness to scale*: ρ captures relative ordering without being sensitive
   to absolute Sharpe values, which vary across sessions due to different
   search space coverage. Winner identity voting collapses the entire ranking
   to a single point; Sharpe overlap requires distributional assumptions.
3. *Graceful degradation*: ρ ∈ [-1, 1] provides a continuous signal. Threshold
   selection for convergence levels maps directly to ρ values
   (e.g., ρ > τ_family for family-level convergence). Top-K Jaccard is a
   useful secondary metric for quick interpretation but loses ordinal
   information.

**However**, Spearman ρ requires a **common comparison domain** — candidates
must be identifiable across sessions. This is exactly SSE-D-04 field 2
(`common_comparison_domain`), which Topic 018 confirmed as a 013 obligation.
The convergence algorithm MUST define: (a) what constitutes the "same candidate"
across sessions (→ consumes SSE-04-IDV from Topic 008), and (b) how to handle
candidates that appear in some sessions but not others (partial overlap). For
candidates absent from a session's ranking, the framework should assign them
rank = K+1 (worst possible), producing a conservative convergence estimate.

**On statistical tests**: The finding proposes bootstrap, permutation, and
majority voting. I argue the convergence verdict should use a
**permutation test** against the null hypothesis "sessions are interchangeable"
(i.e., session labels carry no information about candidate rankings). This is
the most appropriate test because:

1. It is non-parametric and makes no distributional assumptions about Sharpe
   ratios.
2. It directly tests the question of interest: do sessions agree on rankings
   more than chance?
3. It produces a p-value that can be thresholded at campaign-declared α
   (not framework-fixed α), allowing campaigns to choose their own
   stringency.

The permutation test should be seeded (deterministic permutation schedule) to
satisfy reproducibility. Bootstrap is appropriate as a diagnostic for confidence
interval estimation on ρ, but should not be the primary convergence test.

**Proposed amendment**: ACCEPT the 4-part structure. Freeze the architectural
choices: (1) hierarchical 4-level convergence verdict, (2) Spearman ρ as
primary metric with Top-K Jaccard as auxiliary, (3) permutation test as
convergence significance test with seeded schedule, (4) common comparison
domain consuming SSE-04-IDV interface. Numeric thresholds (τ_family,
τ_structural, τ_full, K for top-K, permutation schedule size) are calibration
parameters owned by this topic but need not be frozen until implementation —
the *architecture* of the metric pipeline is what must be frozen.

### Classification: Thiếu sót

---

## CA-02: Stop conditions & diminishing returns — ACCEPT with amendments

### Position

The finding correctly identifies a three-part gap (within-campaign sessions,
cross-campaign same-data, MK-17 interaction) and provides a sound decomposition.
I accept the structure and propose amendments to tighten the architecture.

**Key argument**: Stop conditions must be *evidence-triggered*, not
*count-triggered*. The finding's open question "Trần mặc định sessions per
campaign? (3? 5? adaptive?)" implies a ceiling-based model. I argue the
framework should use a **convergence-delta model** — the stop condition fires
when convergence progress stalls, not when a count is reached.

**Part 1 — Within-campaign (session count)**:

The finding proposes 3 criteria (information gain, novel candidate rate, winner
stability). These are not independent — they are ordered projections of the
same underlying signal (convergence delta). I propose a unified formulation:

**Primary stop criterion**: `Δρ(N, N-1) < ε` for `M` consecutive sessions,
where `Δρ(N, N-1)` is the change in pairwise Spearman ρ when session N is
added to the pool. This directly measures whether adding sessions changes the
convergence picture. If adding 3 consecutive sessions does not move the
convergence metric by more than ε, the information gain is exhausted.

**Secondary stop criterion**: Winner stability — the top-1 candidate (by
aggregated rank) is unchanged for `M` consecutive sessions. This is a
necessary-but-not-sufficient condition: stable winner with unstable rankings
may indicate a dominant outlier, not genuine convergence.

**Hard ceiling**: A maximum session count per campaign must exist as a
resource bound, not a convergence judgment. The framework should distinguish
between `CONVERGED_STOP` (primary/secondary criteria met) and `CEILING_STOP`
(resource bound reached without convergence). `CEILING_STOP` is NOT a verdict
of divergence — it means the campaign's search space may require more sessions
than allocated, and the operator must decide whether to extend (human override)
or accept the partial convergence state.

**Evidence**: Topic 001 Decision 3 (D-16) froze the HANDOFF trigger vocabulary
`{convergence_stall, methodology_gap}`. The `convergence_stall` trigger
is exactly a `CEILING_STOP` condition — it fires when the campaign cannot
converge within its allocated sessions. The stop criterion framework must
produce the signal that triggers HANDOFF.

**Part 2 — Cross-campaign (same-data ceiling)**:

The finding correctly connects this to MK-17. I argue the same-data ceiling
should be *derived from diminishing returns*, not *fixed a priori*. However,
a hard maximum is still needed as a safety valve.

**Architecture**: Each same-data campaign C_k (k > 1) must demonstrate that
its methodology change produces a *measurably different convergence landscape*
compared to C_{k-1}. "Measurably different" means the converged candidate set
(top-K rankings) changes beyond the equivalence threshold (→ SSE-04-THR).
If two consecutive same-data campaigns produce equivalent top-K sets despite
different methodologies, the same-data space is exhausted regardless of k.

This is superior to a fixed ceiling because:
1. A fixed ceiling (e.g., 5) may be too high for simple search spaces (wasting
   resources) or too low for complex ones (premature stop).
2. Equivalence-based exhaustion directly tests the question: "does different
   methodology produce different answers on the same data?"

**Hard ceiling interaction with MK-17**: MK-17 (shadow-only, Topic 004 CLOSED)
means same-data campaigns cannot learn from prior campaign results. Each
campaign is approximately independent. This means diminishing returns are
driven by *methodology exhaustion* (running out of novel approaches), not
*information accumulation* (each campaign learns from the previous). The stop
criterion should detect methodology exhaustion: if the HANDOFF dossier's
`proposed_change` is equivalent to a prior campaign's methodology, the campaign
is redundant.

**Part 3 — `NO_ROBUST_IMPROVEMENT` policy**:

The framework must operationalize Topic 007 Decision 1 (D-01): when convergence
analysis produces `NO_ROBUST_IMPROVEMENT`, this is a valid campaign exit. The
stop condition framework must distinguish:

- `CONVERGED_STOP` + robust candidate → `INTERNAL_ROBUST_CANDIDATE` (Topic 007
  campaign-tier verdict)
- `CONVERGED_STOP` + no robust candidate → `NO_ROBUST_IMPROVEMENT` (valid exit
  per F-01)
- `CEILING_STOP` + no robust candidate → `HANDOFF` or
  `NO_ROBUST_IMPROVEMENT` (human decision)

The `NO_ROBUST_IMPROVEMENT` path requires that the convergence analysis itself
was valid (sessions ran, convergence was measured, the answer is "nothing passes
the bar") — it is not a default for failed campaigns.

**Proposed amendment**: ACCEPT the 3-part structure. Freeze:
(1) convergence-delta stop criterion (`Δρ < ε` for M sessions) as primary,
winner stability as secondary, hard ceiling as resource bound;
(2) same-data campaign exhaustion via equivalence-based methodology comparison,
with hard ceiling as safety valve;
(3) `NO_ROBUST_IMPROVEMENT` exit path connected to Topic 007 D-01 and Topic
001 D-16 HANDOFF vocabulary.
Numeric values (ε, M, hard ceilings) are calibration parameters, not
architectural decisions.

### Classification: Thiếu sót

---

## SSE-09: Scan-phase correction law default — ACCEPT with amendment

### Position

Topic 018 confirmed (SSE-D-09, Converged R2) that multiplicity control is
coupled to the breadth-activation contract via SSE-D-04 field 5
(`scan_phase_correction_method`). The architectural obligation is clear: Topic
013 must specify the default correction formula, a v1 recommendation, and
threshold calibration methodology. I accept this obligation and propose a
specific architectural position.

**Key argument**: The choice between Holm (step-down, controls FWER) and BH
(controls FDR) is not a trading threshold decision (prohibited by `rules.md`
§19) — it is a **framework design decision** about the scan phase's error
control philosophy. The two approaches answer different questions:

- **FWER (Holm)**: "What is the probability that ANY rejected null is a false
  discovery?" Conservative. Appropriate when each false discovery has high cost.
- **FDR (BH)**: "What is the PROPORTION of rejections that are false
  discoveries?" Balanced. Appropriate when the scan phase feeds a downstream
  validation pipeline that catches false positives.

Alpha-Lab's architecture has a natural two-pass structure: the scan phase
generates candidates, and the validation pipeline (7 gates per
`CLAUDE.md:validation`) evaluates them rigorously. This means a false discovery
in the scan phase is caught by downstream gates — the cost of a scan-phase
false positive is wasted compute, not deployment of a bad strategy. Under this
architecture, FDR control is the appropriate error philosophy for the scan
phase because it optimizes the tradeoff between discovery breadth (finding
genuine candidates) and compute waste (evaluating false positives).

**However**, the correction method must be **protocol-declared**, not
**framework-fixed**. SSE-D-04 field 5 requires each protocol to declare its
correction method. This means the framework provides a *default* (FDR/BH),
but protocols can override it with stricter control (Holm) if the scan phase
operates in a context where false discoveries are more costly (e.g., a
breadth expansion that bypasses some validation gates).

**Evidence**: The two-pass structure is established in `design_brief.md:55-72`
(8-stage pipeline) and `PLAN.md:633-670` (V6 pipeline). Scan phase is Stages
3-4; validation is Stages 5-8. The scan phase's job is *recall* (find all
plausible candidates), while validation's job is *precision* (reject false
positives). FDR aligns with recall-oriented phases; FWER aligns with
precision-oriented phases.

**On cascade correction**: Cascade (layered testing with increasing stringency)
is an implementation pattern, not an alternative to Holm/BH. A cascade can use
either FWER or FDR at each level. The framework should not specify cascade vs
flat as an architectural choice — this is a protocol implementation detail
within the declared correction method.

**On interaction with cell-elite diversity preservation**: The finding asks
about interaction with cell-elite's diversity preservation (Topic 017). The
tension is real: aggressive correction (Holm) at the scan phase kills rare
but genuine candidates, undermining diversity; permissive correction (BH)
preserves diversity but increases compute cost. This tension is resolved by
the two-pass architecture: BH at scan phase preserves diversity, validation
pipeline enforces quality. Cell-elite's diversity preservation operates within
the set that *passes* scan-phase correction — it does not override the
correction itself.

**Proposed amendment**: ACCEPT the obligation. Freeze: (1) v1 default =
BH (FDR control) for scan phase, motivated by two-pass architecture where
scan optimizes recall; (2) protocol-declared override (any FWER/FDR method)
per SSE-D-04 field 5; (3) cascade is an implementation pattern within the
declared method, not a separate architectural choice; (4) interaction with
017 cell-elite: correction precedes diversity preservation, not vice versa.

### Classification: Thiếu sót

---

## SSE-04-THR: Equivalence + anomaly thresholds — ACCEPT with amendments

### Position

Topic 018 confirmed (SSE-D-06, Converged R2) hybrid equivalence (structural
pre-bucket + behavioral nearest-rival) and (SSE-D-05, Judgment call R6) a
working minimum inventory of 5 anomaly axes + 5 proof components. Topic 008
Decision 4 (SSE-04-IDV, Converged R2) established the ownership split: 008
owns structural pre-bucket fields, 013 owns equivalence semantics, 017 owns
consumption. I accept these upstream constraints and propose architectural
positions for the 4 obligations in this topic's scope.

**Key argument**: The 4 obligations (behavioral threshold, structural hash
granularity, robustness bundle minimums, anomaly axis thresholds) must be
specified as **framework-level methodology**, not hardcoded constants. Each
obligation should have: (a) a specification of *what is measured*, (b) a
calibration *procedure* for determining thresholds, and (c) a default value
or range that the v1 protocol can use before empirical calibration.

**1. Behavioral equivalence distance threshold (ρ cutoff)**:

The behavioral nearest-rival audit uses paired-return correlation (ρ) to
detect functional equivalence. The architectural question is not "what ρ
value" (calibration) but "what does the threshold control and how is it set?"

I argue the threshold should be calibrated via the **false-equivalence cost**:
declaring two genuinely different candidates as equivalent (false equivalence)
wastes one candidate; declaring two identical candidates as different (false
non-equivalence) wastes compute on redundant evaluation. In a scan phase
optimizing for recall (per SSE-09 above), false non-equivalence is cheaper
than false equivalence. This means the threshold should err conservative
(higher ρ required for equivalence declaration), preserving candidate
diversity at the cost of some redundant evaluation.

The calibration procedure should be: given a protocol's candidate set, compute
pairwise ρ and examine the distribution. The threshold should be set at a
natural gap in the ρ distribution (if one exists) or at a protocol-declared
default. This is a data-driven calibration, not a universal constant.

**2. Structural hash granularity for pre-bucketing**:

Topic 008 Decision 4 specifies structural pre-bucket fields: descriptor hash,
parameter family, AST-hash subset. The semantic question for 013 is: **at what
granularity does the structural hash distinguish candidates?**

I argue the granularity should be **architecture-level** (same family +
same structural composition = same bucket), not parameter-level. Parameter
differences within the same architecture are captured by the behavioral layer;
the structural pre-bucket's job is to *reduce the comparison space* by
grouping architecturally identical candidates before the more expensive
behavioral comparison runs.

**Evidence**: Topic 008's structural pre-bucket fields (descriptor hash,
parameter family, AST-hash subset) are architecture-level descriptors. The
"AST-hash subset" specifically captures structural composition while abstracting
over parameter values. This is consistent with the hybrid design intent:
structural pre-bucket handles architecture-level grouping, behavioral
nearest-rival handles parameter-level equivalence within a bucket.

**3. Robustness bundle minimum requirements**:

Topic 018 SSE-D-05 (Judgment call) established a working minimum inventory of
5 proof components: `nearest_rival_audit`, `plateau_stability_extract`,
`cost_sensitivity_test`, `dependency_stressor`, `contradiction_profile`. The
question for 013 is: what constitutes "minimum" numerically — must all 5 pass?
Any 3? Weighted scoring?

I argue the architecture should use a **mandatory-all model**: all 5 proof
components must be *attempted* for every candidate that enters the proof
bundle stage. However, not all components produce a pass/fail verdict — some
are diagnostic (e.g., `contradiction_profile` may be empty if no prior
contradiction exists). The architectural distinction is between:

- **Gate components** (must pass): `nearest_rival_audit` (candidate is
  genuinely distinct from nearest rival), `dependency_stressor` (candidate
  survives perturbation/ablation)
- **Characterization components** (must complete, verdict is informative):
  `plateau_stability_extract`, `cost_sensitivity_test`, `contradiction_profile`

This 2+3 split ensures that the minimum quality bar is enforced via gates
while preserving diagnostic information for downstream consumption (Topic 017
ESP, Topic 003 protocol engine).

**However**, SSE-D-05 was adopted at Judgment call authority — not Converged.
The working minimum inventory is explicitly "NOT described as immutable
historically-converged exact label set" (`018-search-space-expansion/
final-resolution.md:134`). Topic 013 should consume the inventory as given
but flag that changes to the 5+5 set require an explicit downstream finding
per the Judgment call terms.

**4. Anomaly axis thresholds (shared with 017)**:

Topic 018 SSE-D-05 named 5 anomaly axes: `decorrelation_outlier`,
`plateau_width_champion`, `cost_stability`, `cross_resolution_consistency`,
`contradiction_resurrection`. The question for 013 is: how are thresholds
set for each axis?

I argue anomaly thresholds must be **relative to the cell population**, not
absolute. An absolute threshold (e.g., "ρ < 0.2 = decorrelation outlier")
is asset-class-dependent and market-regime-dependent. A relative threshold
(e.g., "decorrelation ρ below the 5th percentile of the candidate population")
adapts to the data and satisfies the asset-agnostic design principle
(CA-01 open question 4).

The calibration procedure: each anomaly axis produces a scalar per candidate.
The threshold is defined as a percentile of the population distribution,
declared per-protocol. The default percentile should be conservative (e.g.,
flagging only extreme outliers) to avoid flooding the surprise queue with
marginal anomalies. The exact percentile is a calibration parameter, not an
architectural constant.

**Ownership boundary with 017**: Topic 013 owns the threshold *methodology*
(relative-to-population, percentile-based). Topic 017 owns the threshold
*consumption semantics* (how the surprise queue uses anomaly flags). The
boundary is: 013 computes "candidate X is anomalous on axis Y at the p-th
percentile"; 017 decides what happens to anomalous candidates.

**Proposed amendment**: ACCEPT all 4 obligations. Freeze: (1) behavioral
equivalence threshold calibrated via false-equivalence cost analysis,
conservative default (higher ρ for equivalence), data-driven per protocol;
(2) structural hash at architecture-level granularity, consuming 008's
pre-bucket fields; (3) robustness bundle = mandatory-all with 2 gate + 3
characterization split; (4) anomaly thresholds relative to cell population
(percentile-based), shared ownership boundary: 013 computes, 017 consumes.

### Classification: Thiếu sót

---

## Summary

### Accepted (near-convergence candidates)

All 4 findings are accepted in substance. The gaps identified by F-30, F-31,
and the routed issues SSE-09, SSE-04-THR are genuine and architecturally
critical. The upstream dependency chain is fully resolved (Topics 001, 004,
007, 008, 018 all CLOSED), providing clear architectural constraints.

### Challenged (need debate)

The amendments proposed are substantive and require Codex's response before
convergence:

- **CA-01**: Hierarchical 4-level convergence verdict (vs finding's 3-level);
  Spearman ρ as primary metric; permutation test as convergence significance
  test; common comparison domain design.

- **CA-02**: Convergence-delta stop model (vs count-ceiling model);
  equivalence-based same-data exhaustion; `NO_ROBUST_IMPROVEMENT` exit path
  operationalization; distinction between `CONVERGED_STOP` and `CEILING_STOP`.

- **SSE-09**: BH (FDR) as v1 default (vs Holm); two-pass architecture
  motivation; cascade as implementation pattern, not architectural choice;
  correction precedes diversity preservation.

- **SSE-04-THR**: Conservative behavioral ρ threshold; architecture-level
  structural hash granularity; 2+3 gate/characterization split for robustness
  bundle; population-relative anomaly thresholds; ownership boundary with 017.

---

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 017 | ESP-01, ESP-04 | Coverage metrics overlap convergence measurement (CA-01). Budget governor coverage obligation interacts with campaign stop conditions (CA-02): coverage floor chưa đạt → extend campaign? | 013 owns convergence metrics and stop conditions; 017 defines coverage obligations for budget governor. Stop conditions fire on convergence delta, not coverage — if coverage is insufficient, 017's budget governor extends the campaign independently of 013's convergence signal. |
| 018 | SSE-09, SSE-04-THR | Routing confirmed. SSE-D-09 and SSE-D-04/05 provide binding interface constraints. | 013 implements within upstream-frozen interfaces. No tension — clean handoff. |
| 008 | SSE-04-IDV | 013's behavioral equivalence threshold (SSE-04-THR) must be compatible with 008's structural pre-bucket (SSE-04-IDV, Decision 4). | 008 owns structural pre-bucket fields; 013 owns behavioral semantics. The 2-layer hybrid design (structural pre-bucket → behavioral nearest-rival) is the compatibility mechanism — no new tension. |
| 001 | D-03, D-16 | Topic 001 deferred numeric convergence floors and session ceilings to 013. HANDOFF trigger `convergence_stall` depends on 013's stop condition signal. | 013 produces convergence signal; 001 consumes it via HANDOFF trigger vocabulary. 013 must produce output compatible with 001's routing contract matrix. |
| 007 | D-01 | `NO_ROBUST_IMPROVEMENT` as valid campaign exit (F-01) depends on 013's convergence analysis being valid — convergence was measured, answer is "nothing passes the bar". | 007 provides constraint; 013 operationalizes it via `CONVERGED_STOP` + no robust candidate path. |

---

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-CA-01 | Convergence measurement framework: hierarchical 4-level verdict, Spearman ρ primary metric, permutation test, common comparison domain | Thiếu sót | Open | "3-level (FULLY/PARTIALLY/NOT) đủ — thêm level là over-engineering" | 3-level model conflates two qualitatively different "partial" states: STRUCTURALLY_CONVERGED (same architecture, different params — plateau evidence) vs FAMILY_CONVERGED (different architectures — weaker signal). V4→V8 record shows exactly this distinction: "D1 slow" family convergence with architecture divergence. The 4th level costs zero implementation complexity (it is a finer partition of PARTIALLY). |
| X38-CA-02 | Stop conditions: convergence-delta model (Δρ < ε for M sessions), equivalence-based same-data exhaustion, NO_ROBUST_IMPROVEMENT exit path, CONVERGED_STOP vs CEILING_STOP distinction | Thiếu sót | Open | "Fixed ceiling (e.g., 5 sessions) đơn giản hơn và đủ cho v1" | Fixed ceiling is count-based, not evidence-based — it cannot distinguish between "5 sessions exhausted the space" and "5 sessions were insufficient." Convergence-delta model is equally simple to implement (compare ρ values) but produces an *informative* stop signal that feeds HANDOFF trigger vocabulary (Topic 001 D-16). |
| X38-SSE-09 | Scan-phase correction: BH (FDR) as v1 default, protocol-declared override per SSE-D-04 field 5, cascade is implementation pattern | Thiếu sót | Open | "Holm (FWER) mặc định an toàn hơn — false discovery ở scan phase vẫn tốn compute" | Holm controls FWER (probability of any false discovery), killing rare-but-genuine candidates at breadth. Alpha-Lab's two-pass architecture (scan → validation) means scan-phase false positives are caught by 7 downstream gates — cost is wasted compute, not bad deployment. FDR controls expected proportion of false discoveries, optimizing the recall/compute tradeoff. |
| X38-SSE-04-THR | Equivalence + anomaly thresholds: conservative behavioral ρ, architecture-level structural hash, 2+3 robustness bundle split, population-relative anomaly thresholds | Thiếu sót | Open | "Absolute thresholds đơn giản và reproducible hơn — population-relative thresholds thay đổi theo data" | Absolute thresholds are reproducible but NOT portable: a decorrelation cutoff calibrated on BTC is meaningless on equities (CA-01 open Q4 asks asset-agnostic). Population-relative thresholds are equally reproducible (same data + same percentile = same threshold) and adapt to the candidate population's distributional properties. |
