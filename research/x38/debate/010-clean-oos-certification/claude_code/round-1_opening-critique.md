# Round 1 — Opening Critique: Clean OOS & Certification

**Topic**: 010-clean-oos-certification
**Author**: claude_code
**Date**: 2026-03-25
**Scope**: X38-D-12 (Clean OOS protocol), X38-D-21 (INCONCLUSIVE verdict),
           X38-D-23 (Pre-existing candidates), X38-D-24 (Power rules)
**Input documents**:
- `research/x38/AGENTS.md`
- `research/x38/docs/online_vs_offline.md`
- `research/x38/x38_RULES.md`
- `research/x38/debate/rules.md`
- `research/x38/debate/prompt_template.md`
- `research/x38/debate/010-clean-oos-certification/README.md`
- `research/x38/debate/010-clean-oos-certification/findings-under-review.md`
- `research/x38/docs/design_brief.md`
- `research/x38/PLAN.md`
- `research/x38/drafts/architecture_spec.md`
- `research/x38/debate/007-philosophy-mission/final-resolution.md`
- `research/x38/debate/001-campaign-model/final-resolution.md`
- `research/x38/debate/002-contamination-firewall/final-resolution.md`
- `research/x37/docs/gen1/RESEARCH_PROMPT_V[n]/PROMPT_FOR_V[n]_CLEAN_OOS_V2[en].md` [extra-archive]
- `validation/thresholds.py` [extra-archive]

---

## Preamble

As architect, I designed the preliminary Clean OOS lifecycle in `design_brief.md`
§4 and the findings under review (F-12, F-21, F-23, F-24). This opening critique
examines whether those findings, as written, are sufficient for blueprint-grade
specification — or whether they contain gaps, under-specified mechanisms, or
classification errors that debate must resolve.

Per `debate/rules.md` §5, the burden of proof lies with the party proposing
change. For issues classified as *Thiếu sót* (F-21, F-23, F-24), I must
demonstrate that the current design is incomplete and that the proposed addition
is necessary. For the *Judgment call* (F-12), I must make the tradeoffs explicit
and identify what evidence would resolve the judgment. The upstream dependencies
are satisfied: Topic 007 (CLOSED) established the 3-tier claim model with
Certification tier verdicts `CLEAN_OOS_CONFIRMED / INCONCLUSIVE / FAIL`
(`architecture_spec.md` §5.2), and Topic 001 (CLOSED) defined the HANDOFF law
and transition-routing contract that governs the Phase 1 → Phase 2 boundary.
Topic 002 (CLOSED) established the contamination firewall enforcement mechanism
that Clean OOS must integrate with.

Topic 010 contains 4 separate findings (F-12, F-21, F-23, F-24). They are
thematically related — all concern the Clean OOS protocol and certification
lifecycle — but each has its own issue ID and must be debated as an independent
design question. Convergence on one does not imply convergence on the others.
I note three cross-topic tensions documented in the topic README: with Topic 003
(protocol pipeline integration), Topic 016 (recalibration interaction), and
Topic 017 (power floor consumption). These tensions are acknowledged but not
owned by Topic 010; resolution paths are recorded in the cross-topic table.

---

## X38-D-12: Clean OOS via future data — ACCEPT with amendment

### Position

The Clean OOS lifecycle described in F-12 is structurally sound. The 4-phase
model (Research → Wait → Clean OOS → Research-again-if-FAIL) correctly
translates the source protocol's intent: discovery and selection happen on the
historical archive, genuine validation happens only on appended future data,
and the reserve opens exactly once. The auto-trigger mechanism (framework creates
`PENDING_CLEAN_OOS` obligation when winner + sufficient data exist) with explicit
defer is good governance — it prevents silent indefinite postponement while
preserving human scheduling discretion. These elements are well-supported by
evidence.

**Key argument**: The mechanism is accepted; the remaining open question —
minimum reserve duration — should NOT be resolved within F-12. Duration is a
power question. It depends on trade frequency, effect size target, and
statistical test choice, all of which belong to F-24 (power rules). Fixing
a duration floor (6 months, 12 months) inside F-12 without the power analysis
from F-24 would be a threshold chosen backward — picking the number first,
then hoping it provides adequate power.

**Evidence**:
- `PROMPT_FOR_V[n]_CLEAN_OOS_V2[en].md`:166-172 [extra-archive] — the source
  protocol's `DATA_PREPARATION_GUIDE` deliverable explicitly couples minimum
  reserve to "trade frequency actually observed in the current session's
  competitive frontier", not to a fixed calendar floor.
- `design_brief.md`:139-143 — already states Clean reserve opens "đúng 1 lần"
  (exactly once), confirming the one-shot constraint.
- `architecture_spec.md` §1.3.4 — transition-routing contract (Topic 001) defines
  "new data appended / Clean OOS fail restart" as a distinct routing row,
  confirming the Phase 2 → Phase 3 transition is already specified.

**However**, two sub-questions remain genuinely open within F-12's scope (not
delegable to F-24):

1. **Module boundary**: Is Clean OOS a standalone module invoked once after
   research, or an integrated stage within the 8-stage protocol pipeline? The
   cross-topic tension with Topic 003 (F-05) notes this ambiguity. Clean OOS
   runs AFTER the research pipeline completes — it is not Stage 9. It should
   be specified as a separate lifecycle phase with its own entry conditions
   (frozen winner exists + power floor met), not appended to the research
   pipeline stages.

2. **FAIL → provenance recording**: When Clean OOS returns FAIL and the cycle
   restarts, F-12 states the failed winner becomes "historical evidence/provenance
   (KHÔNG nâng thành anti-pattern)". This is correct per
   `PROMPT_FOR_V[n]_CLEAN_OOS_V2[en].md`:30 [extra-archive] ("no redesign, no
   retuning, no winner switching"). But the provenance format is unspecified.
   The contamination firewall (Topic 002) provides `MetaLesson` typed schema
   with 3 whitelist categories — a failed Clean OOS verdict does not fit any
   of them (it is not `PROVENANCE_AUDIT_SERIALIZATION`, `ANTI_PATTERN`, or
   `SPLIT_HYGIENE`). The failed verdict needs its own provenance record outside
   the meta-lesson schema, or the schema needs a recording path for it.

**Proposed amendment**: (a) F-12 delegates minimum duration entirely to F-24.
F-12 specifies only that Clean OOS MUST NOT open before F-24's power floor is
met. (b) F-12 specifies Clean OOS as a separate lifecycle phase (not a pipeline
stage). (c) F-12 defines the FAIL provenance record format or explicitly creates
an interface requirement for Topic 002/004 to resolve.

### Classification: Judgment call

The mechanism is settled. The module boundary and provenance format are judgment
calls about where in the architecture these responsibilities land (010 vs 003
vs 002/004). The minimum duration is delegated to F-24.

---

## X38-D-21: CLEAN_OOS_INCONCLUSIVE — first-class verdict state — ACCEPT with amendment

### Position

The need for `CLEAN_OOS_INCONCLUSIVE` as a first-class verdict is
well-established and already integrated into the architecture. Topic 007
(CLOSED) froze the 3-tier claim model with `CLEAN_OOS_INCONCLUSIVE` as an
explicit certification-tier verdict (`architecture_spec.md` §5.2). The source
protocol is unambiguous: "if the clean reserve is too short, too sparse, or
otherwise underpowered, the session must use an honest **inconclusive** label
rather than overstating certainty" (`PROMPT_FOR_V[n]_CLEAN_OOS_V2[en].md`:78-82
[extra-archive]). The btc-spot-dev pre-existing candidate's WFO underresolved
status (Wilcoxon p=0.125 at N=8, `validation/thresholds.py`:57-58 [extra-archive])
is direct empirical precedent for insufficient power on internal data — the same
problem will recur on appended data if the reserve is too short.

**Key argument**: INCONCLUSIVE is accepted as necessary. The open question —
whether INCONCLUSIVE has an upper bound (maximum iterations before forced
FAIL) — reveals a genuine tension between two principles:

- **Honest labeling**: if evidence is genuinely insufficient, forcing FAIL is
  scientifically dishonest. The label should reflect epistemic state, not
  administrative fatigue.
- **Practical termination**: without any bound, INCONCLUSIVE becomes a permanent
  parking lot. A winner could sit in INCONCLUSIVE indefinitely if the market
  generates too few trades or stays in a single regime.

**Evidence**:
- `PROMPT_FOR_V[n]_CLEAN_OOS_V2[en].md`:78-82 [extra-archive] — "honest
  inconclusive label" principle.
- `architecture_spec.md` §5.2 — INCONCLUSIVE already in verdict taxonomy.
- F-12 lifecycle: INCONCLUSIVE → "giữ INTERNAL_ROBUST_CANDIDATE, chờ thêm data"
  — candidate stays at campaign tier, does not regress to pre-candidate.

**However**, the finding as written provides no mechanism to distinguish
"genuinely underpowered, wait more" from "perpetually underpowered, this
strategy will never accumulate enough evidence." Consider: a strategy with
~20 trades/year on BTC. At 6-month reserves, each INCONCLUSIVE attempt yields
~10 trades. Wilcoxon at N=10 has minimum achievable p ≈ 0.001 but practical
power against moderate effects is still low. After 3 attempts (18 months), the
candidate has consumed 18 months of operational time with no resolution. A
fourth attempt is statistically identical to the third.

**Proposed amendment**: Each INCONCLUSIVE verdict MUST include a **prospective
power projection**: given observed trade frequency and effect size in the
current reserve, how many additional months/trades are needed for the next
attempt to reach target power (e.g., 80% power at the pre-registered effect
size from F-24)? If the projection shows that no feasible future window can
achieve target power (e.g., strategy trades too infrequently for any
reasonable reserve to be powered), the framework escalates to human judgment
with an explicit `POWER_INFEASIBLE` flag — not automatic FAIL, but a forced
decision point. This preserves honest labeling while preventing indefinite
parking.

### Classification: Thiếu sót

The verdict state itself is established (Topic 007). The missing piece is the
iteration governance mechanism — what happens after repeated INCONCLUSIVEs.
This is a gap in the current specification, not a design error or judgment call.

---

## X38-D-23: Pre-existing candidates vs x38 winners — ACCEPT with SPLIT

### Position

F-23 identifies a genuine gap: the design does not specify how pre-existing
candidates from the online research process (E5_ema21D1, currently HOLD)
interact with x38 framework winners. The 3 scenarios (rediscovery, different
family, NO_ROBUST_IMPROVEMENT) are correctly enumerated and each has distinct
implications.

**Key argument**: This finding conflates two concerns that should be split:

**(A) Protocol-level interface** (x38 scope): How does x38 record, track, and
reference pre-existing candidates? This is a contamination/provenance question.
MK-17 (Topic 004, CLOSED) already answers the core rule: on the same dataset,
pre-existing candidate empirical priors are **shadow-only**. The x38 pipeline
must know the pre-existing candidate exists (for provenance), but must not use
it to narrow search space. This interface belongs in the blueprint.

**(B) Operational adjudication** (outside x38 scope): If x38 produces a
different winner than the pre-existing candidate, who arbitrates? Parallel
Clean OOS? Head-to-head on appended data? Priority rules? These are deployment
decisions that depend on resource constraints, risk appetite, and operational
context — exactly the concerns `x38_RULES.md` §19 excludes from debate
("Không tranh luận về... Deployment, paper trading, production concerns").

**Evidence**:
- `architecture_spec.md` §5.2 — 3-tier claim model: pre-existing candidate
  (HOLD verdict from btc-spot-dev validation) sits at campaign tier
  (`INTERNAL_ROBUST_CANDIDATE`). It has no certification-tier status.
- Topic 004 MK-17 (CLOSED): same-dataset empirical priors = shadow-only
  (`design_brief.md`:87-89).
- `PLAN.md`:504-519 — Phase 2 replays "frozen winner" (x38's own). This is
  by design, not an oversight: Clean OOS validates x38's independent finding.
- `x38_RULES.md` §19 — debate scope excludes deployment/operational concerns.

**However**, the protocol-level interface (Part A) has a real gap: the
`CleanOOSConfig` dataclass in F-12 has no field for pre-existing candidate
reference. When x38 produces a winner, the provenance chain should record
whether that winner is from the same family as the pre-existing candidate
(convergent evidence) or a different family (contradiction). This is not
operational adjudication — it is provenance metadata that the framework must
capture regardless of what happens downstream.

**Proposed amendment**: SPLIT F-23 into:
- **D-23a** (Protocol interface, x38 scope): Pre-existing candidates are
  recorded in campaign provenance as shadow-only references per MK-17. The
  Clean OOS config includes an optional `pre_existing_candidate_ref` field
  (provenance pointer, not active prior). The research output includes a
  mandatory `convergence_with_pre_existing` classification
  (`SAME_FAMILY | DIFFERENT_FAMILY | NO_COMPARISON`). This is a Thiếu sót
  that the blueprint should fix.
- **D-23b** (Operational adjudication, deferred): How to adjudicate when x38
  and pre-existing disagree (parallel Clean OOS, priority, etc.) is deferred
  to the deployment layer. x38 provides the provenance data; the deployment
  layer decides what to do with it.

### Classification: Thiếu sót (for D-23a) / Defer to V2+ (for D-23b)

The protocol interface gap is real and fixable. The operational adjudication
question is legitimate but out of scope per §19.

---

## X38-D-24: Clean OOS power rules — ACCEPT with amendment

### Position

Pre-registered power rules for Clean OOS are essential. Without them, the
CONFIRMED/FAIL/INCONCLUSIVE boundary becomes a post-hoc judgment call —
exactly the kind of subjective decision the offline framework exists to
eliminate. The finding correctly identifies 5 power dimensions (trade count,
time coverage, regime coverage, exposure hours, effect size) and correctly
argues for pre-registration over post-hoc assessment.

**Key argument**: The finding's 5-dimension power table is a reasonable
starting point but contains one problematic dimension and one critical
methodological gap.

**Problematic dimension — regime coverage**: The proposal requires "≥ 2
distinct regimes (trend + chop, hoặc bull + bear)" in the reserve. This is
problematic for three reasons:

1. **Regime classification is itself a judgment call**. What defines a "distinct
   regime"? If the D1 EMA(21) filter is used, we leak strategy-specific
   knowledge into the power rules. If we use an external classifier
   (volatility bands, trend/mean-reversion), we introduce a dependency on
   classifier design — itself a research question.

2. **Regime coverage is not controllable**. Unlike trade count (which can be
   projected from frequency) and time coverage (which is calendar-based),
   regime coverage depends on market behavior. A 12-month reserve in a
   sustained bull trend will have exactly one regime regardless of duration.
   A binding gate on regime coverage penalizes the framework for market
   conditions, not for methodological failure.

3. **Regime coverage is already partially captured by time coverage**. A
   sufficiently long reserve (e.g., 18+ months for BTC) will almost certainly
   sample multiple regimes. The marginal value of a separate regime gate over
   a time-coverage gate is low.

**Evidence**:
- `validation/thresholds.py`:39-46 [extra-archive] —
  `WFO_SMALL_SAMPLE_CUTOFF = 5` tagged `UNPROVEN`, demonstrating that even
  internal validation has struggled with power threshold calibration.
- `validation/thresholds.py`:55-58 [extra-archive] — WFO Wilcoxon at N=8
  requires W+ ≥ 28/36 to reject. Pre-existing candidate achieved p=0.125.
  This is exactly the kind of underpowered scenario F-24 aims to prevent.
- `PROMPT_FOR_V[n]_CLEAN_OOS_V2[en].md`:166-172 [extra-archive] — source
  protocol couples reserve recommendation to "trade frequency actually observed
  in the current session's competitive frontier" — an effect-size-aware
  approach, not a fixed floor.

**Critical methodological gap — power analysis method**: The finding identifies
this gap ("power analysis method nào phù hợp?") but does not resolve it. The
proposal lists heuristic thresholds (≥ N trades, ≥ M months) without a
derivation path. The correct approach is **method-first**:

1. Choose the statistical test for Clean OOS evaluation (e.g., paired test on
   performance metrics, or bootstrap comparison against a benchmark).
2. Define the minimum effect size worth detecting (ΔSharpe, ΔReturn) — this
   comes from the frozen winner's archive-only performance.
3. Run a priori power analysis (simulation-based for complex test statistics,
   analytical for simple ones) to derive minimum N (trades, windows, months).
4. Pre-register the derived thresholds.

Simulation-based power analysis is most appropriate for Clean OOS because:
- The test statistic is complex (Sharpe ratio comparison, not a simple mean).
- Trade-level data is autocorrelated (bootstrap blocks, not i.i.d.).
- The btc-spot-dev codebase already has VCBB (`research/lib/vcbb.py`
  [extra-archive]) which could serve as the simulation engine.

**However**, the power analysis method itself is a V1 design question, not a
"defer until implementation" question. If the blueprint does not specify the
method, implementers will face the same ambiguity and resort to the same
heuristics.

**Proposed amendment**: (a) Regime coverage is downgraded from binding gate to
advisory diagnostic. It is reported but does not gate CONFIRMED/INCONCLUSIVE.
(b) The blueprint specifies the power analysis METHOD (simulation-based, using
the same bootstrap framework as the research pipeline). (c) The blueprint
specifies that power thresholds are derived per-campaign (not universal
constants), pre-registered before the reserve opens, and frozen thereafter.
(d) Trade count and time coverage remain binding gates. Exposure hours is
retained as binding (prevents strategies that are technically "in the reserve
period" but never trade). (e) Effect size thresholds are pre-registered per
campaign, derived from the frozen winner's archive performance.

### Classification: Thiếu sót

The design is missing both the power analysis method and the threshold derivation
path. These are not judgment calls — there is a correct answer (method-first
derivation) vs an incorrect answer (heuristic floors without derivation).

---

## Summary

### Accepted (near-convergence candidates)

- **X38-D-12**: Mechanism accepted. Module boundary (separate phase, not Stage 9)
  and FAIL provenance format need specification. Minimum duration delegated to
  F-24.
- **X38-D-21**: INCONCLUSIVE verdict accepted (already in §5.2). Needs iteration
  governance: prospective power projection per attempt, `POWER_INFEASIBLE`
  escalation flag.

### Challenged (need debate)

- **X38-D-23**: Proposed SPLIT into protocol interface (D-23a, x38 scope) vs
  operational adjudication (D-23b, defer). The split boundary itself may be
  contested.
- **X38-D-24**: Regime coverage as binding gate is challenged. Power analysis
  method specification is proposed as mandatory V1 content. Per-campaign
  pre-registration vs universal constants needs resolution.

---

## Status Table

| Issue ID | Finding | Classification | Status | Steel-man for opposing position | Reason to reject steel-man |
|---|---|---|---|---|---|
| X38-D-12 | Clean OOS via future data | Judgment call | Open | — | — |
| X38-D-21 | CLEAN_OOS_INCONCLUSIVE verdict | Thiếu sót | Open | — | — |
| X38-D-23 | Pre-existing candidates vs x38 winners | Thiếu sót | Open | — | — |
| X38-D-24 | Clean OOS power rules | Thiếu sót | Open | — | — |
