# Round 1 — Opening Critique: Philosophy & Mission Claims

**Topic**: 007 — Philosophy & Mission Claims
**Author**: claude_code
**Date**: 2026-03-23
**Scope**: All findings — X38-D-01, X38-D-20, X38-D-22, X38-D-25
**Input documents**:
- `debate/rules.md` (full, 211 lines)
- `debate/007-philosophy-mission/findings-under-review.md` (full)
- `debate/007-philosophy-mission/README.md` (full)
- `debate/prompt_template.md` (full)
- `x38_RULES.md` (full, 197 lines)
- `docs/design_brief.md` (full, 221 lines)
- `docs/online_vs_offline.md` (full, 183 lines)
- `docs/evidence_coverage.md` (§1-2)
- `AGENTS.md` (full)
- `PLAN.md` (§Sứ mệnh lines 1-60, §1.4 lines 207-218, §1.4.1 lines 223-244, §2.2 lines 442-509)
- `debate/000-framework-proposal/findings-under-review.md` (convergence notes C-07, C-08, C-10, C-12; finding index)
- `debate/004-meta-knowledge/final-resolution.md` (full — MK-02, MK-05, MK-17 frozen decisions)

---

## Preamble

As the architect who drafted both design_brief.md and PLAN.md, I enter this
debate with dual obligation: defend the decisions I made where evidence supports
them, and expose weaknesses in my own design before they calcify into published
spec. Topic 007 is the foundation — every other topic inherits constraints from
whatever we decide here. An error in philosophy propagates everywhere.

**Burden of proof** (rules.md §5): the existing design (design_brief.md +
PLAN.md) holds unless a critic demonstrates it is wrong or incomplete with
evidence. For the 4 findings under review: F-01 and F-25 defend positions already
present in the design (burden on critic to overturn); F-20 and F-22 identify gaps
in the current design (burden on proposer to show the gap is real and the fix is
correct). Since I am both architect and opening critic, I will be explicit about
when I am defending my own design vs. when I am arguing for changes to it.

**Pre-debate baseline**: Four convergence notes constrain this topic. C-07
establishes that "full rediscovery automated" is aspiration, not fact — we must
not overclaim. C-08 establishes that the 3-tier claim diagnosis has converged
between both agents; only naming remains open. C-10 establishes that F-01 is NOT
self-executing — it requires operationalization through the contamination firewall
(topic 002). C-12 establishes that bounded recalibration is prima facie
incompatible with the current firewall, which constrains how aggressively we
interpret "inherit methodology." Topic 004 (CLOSED) provides frozen invariant
MK-17: same-dataset empirical priors are shadow-only before freeze. This directly
constrains F-01's operational interpretation.

**Scope boundaries**: This topic decides WHAT the framework promises and HOW it
classifies its own claims. It does NOT decide contamination mechanics (topic 002),
campaign operations (topic 001), or protocol stages (topic 003). When findings
here create tensions with those topics, I note the tension and the owning topic
but do not resolve it here.

---

## X38-D-01: Triết lý — kế thừa methodology, không kế thừa đáp án — ACCEPT with amendment

### Position

The core argument is sound and multiply-evidenced. "Inherit methodology, not
answers" follows directly from V6 protocol principles:

> "The target is not a claim of global optimum. The target is the best candidate
> found inside a declared search space, with honest evidence labeling."
> — `RESEARCH_PROMPT_V6.md:7-13` [extra-archive]

V8's result provides the strongest empirical confirmation: V8 winner (S_D1_TREND,
D1 momentum family) is completely different from V7 winner (D1 volatility
clustering family) despite running on the same data with the most refined
governance to date (643 lines, 16 improvements over V7)
(`CONVERGENCE_STATUS_V3.md:5-10` [extra-archive]). If the best-governed online
session cannot guarantee exact winner convergence, then promising "the objectively
best algorithm" would be dishonest. The philosophy is not modesty — it is
intellectual honesty about a demonstrated constraint.

**Key argument**: F-01's classification of `NO_ROBUST_IMPROVEMENT` as a valid
verdict (not failure) is the most architecturally important claim in this finding.
Without it, the framework faces a structural incentive to always declare a
winner — degrading scientific integrity to satisfy a mission framing. V7 handoff
(`PROMPT_FOR_V7_HANDOFF.md:56-59` [extra-archive]) explicitly establishes open
search space with no prior-result bias, and V8 handoff
(`PROMPT_FOR_V8_HANDOFF.md` [extra-archive]) continues this principle. The
NO_ROBUST_IMPROVEMENT verdict directly operationalizes "honest evidence labeling."

**However**, F-01 has an under-specified gap that the finding acknowledges but
does not resolve: the tension between PLAN.md §Sứ mệnh line 7 ("Tìm cho bằng
được thuật toán trading tốt nhất" — aspirational, absolute) and PLAN.md §1.4
lines 212-214 ("Framework KHÔNG hứa cho ra thuật toán tốt nhất" — operational,
bounded). These two statements are NOT contradictory — but they operate at
different levels of commitment, and the finding does not formalize this
distinction. Without formalization, downstream topics risk conflating mission
aspiration with campaign promise. For example: topic 001 (campaign-model) must
decide stop conditions; if the mission is read as "never stop until you find the
best," campaigns cannot terminate with NO_ROBUST_IMPROVEMENT. But if the
operational promise is correctly read as "best within declared search space," then
NO_ROBUST_IMPROVEMENT is a natural campaign exit.

C-10 from pre-debate convergence reinforces this: F-01 alone is insufficient —
it needs operationalization through the firewall. The philosophy declares intent;
the firewall (topic 002) and campaign model (topic 001) enforce it. F-01 should
explicitly acknowledge this enforcement dependency, so that no downstream topic
treats the philosophy as self-executing.

**Proposed amendment**: Formalize the two-level structure within F-01:

1. **Mission level** (PLAN.md §Sứ mệnh): "Tìm cho bằng được thuật toán trading
   tốt nhất" — aspirational, infinite-horizon goal. No single campaign satisfies
   this. The mission drives the framework to iterate (NV1→NV2 cycles), not to
   overclaim within any single cycle.

2. **Operational level** (campaign output): "Strongest candidate within declared
   search space, or honest NO_ROBUST_IMPROVEMENT" — this is what each campaign
   actually delivers. This is the TESTABLE promise.

3. **Enforcement dependency**: F-01 is a declaration of intent, not a
   self-executing constraint. It requires: contamination firewall (topic 002) to
   prevent answer leakage, campaign isolation (topic 001) to ensure each session
   starts from blank slate, and protocol engine (topic 003) to enforce
   methodology inheritance.

This amendment sharpens the argument without changing the conclusion. F-01's open
question "có đủ rõ ràng?" is answered: not yet — but the fix is formalization,
not redesign. Note that this two-level formalization naturally merges with F-20's
three-tier model (see below), which adds Certification as a third level.

### Classification: Judgment call

The core philosophy is correct. The gap (implicit vs. explicit two-level
formalization) is a judgment call: both "implicit is sufficient" and "explicit
formalization needed" are defensible positions. Evidence favors explicit
formalization because downstream topics need an unambiguous reference point.

---

## X38-D-20: 3-tier claim separation — Mission / Campaign / Certification — ACCEPT

### Position

F-20's diagnosis is correct, converged (C-08), and well-evidenced. Three distinct
claim levels exist in the current design but are not formalized as a semantic
model:

- **PLAN.md:7-11**: "tìm cho bằng được thuật toán trading tốt nhất" → mission
- **PLAN.md:209-214**: "candidate mạnh nhất TRONG search space đã khai báo" →
  campaign
- **PLAN.md:451-475**: research (mandatory) vs Clean OOS (conditional) →
  certification as a distinct validation step

The evidence from `CONVERGENCE_STATUS_V3.md:5-10` [extra-archive] confirms the
need: family-level convergence exists but exact-winner convergence does not. This
means campaign verdicts (`INTERNAL_ROBUST_CANDIDATE`) and certification verdicts
(`CLEAN_OOS_CONFIRMED`) have fundamentally different evidentiary strength — and
the framework must not conflate them.

**Key argument**: The verdict taxonomy is well-designed and internally consistent:

| Tier | Claim scope | Verdicts | Evidence type |
|------|-------------|----------|---------------|
| Mission | Infinite-horizon aspiration | None (ongoing) | Accumulation across campaigns |
| Campaign | Within declared search space | `INTERNAL_ROBUST_CANDIDATE`, `NO_ROBUST_IMPROVEMENT` | Internal evidence (same data) |
| Certification | Independent validation | `CLEAN_OOS_CONFIRMED`, `CLEAN_OOS_INCONCLUSIVE`, `CLEAN_OOS_FAIL` | Independent evidence (new data) |

This maps cleanly onto the existing design without structural changes. It is
a formalization of implicit structure, not a redesign.

**However**, the finding raises two open questions that I address:

**1. Naming**: "Mission / Campaign / Certification" is precise and I accept it.
"Certification" correctly implies external, independent verification — the right
connotation for new-data validation. Alternatives ("Validation", "Confirmation")
are weaker: "validation" is overloaded (used for WFO, bootstrap, etc.),
"confirmation" implies a positive outcome rather than an independent test. The
only risk with "Certification" is that it might imply a third-party authority;
this can be clarified in spec prose.

**2. FAMILY_CONVERGED qualifier**: The finding asks whether
`INTERNAL_ROBUST_CANDIDATE` needs sub-state
`FAMILY_CONVERGED_EXACT_UNRESOLVED` for exhausted archives. My position: the
diagnostic information is valuable but verdict name inflation is not the right
mechanism. Campaign verdicts should remain a small, stable enumeration. Instead,
attach **convergence metadata** to the verdict:

```
verdict: INTERNAL_ROBUST_CANDIDATE
convergence_level: family          # enum: exact | family | architecture | none
convergence_sessions: 5            # how many sessions contributed
convergence_evidence: [session_ids]
```

This keeps the verdict taxonomy clean (2 campaign verdicts, 3 certification
verdicts) while preserving diagnostic depth. Downstream consumers (human
researcher, monitoring) can inspect `convergence_level` without needing to parse
compound verdict names.

**Proposed amendment**: Accept the 3-tier model with Mission / Campaign /
Certification naming. Implement `convergence_level` as verdict metadata instead
of verdict sub-states. Note: F-20 naturally absorbs the two-level formalization
proposed for F-01 — the Mission/Campaign distinction IS the formalization F-01
needs.

### Classification: Thiếu sót

Correct. The 3-tier structure is already implicit — formalizing it fills a gap.
This is not a design change; it is making explicit what was already there.

---

## X38-D-22: Phase 1 value classification on exhausted archives — ACCEPT with protocol addition

### Position

F-22's evidence taxonomy is correct and important for preventing overclaim. The
three-way classification:

| Evidence type | Phase 1 on exhausted archive? | Example |
|---------------|-------------------------------|---------|
| Coverage/process | **Yes** | "50K+ features scanned, converge on D1 slow family" |
| Deterministic convergence | **Yes** | "N sessions, same leader" |
| Clean adjudication | **No** | Requires genuinely new data |

…is directly supported by PLAN.md:497-498 ("Same-file methodological tightening
cải thiện governance, KHÔNG tạo clean OOS evidence mới") and by the fundamental
constraint that no framework can manufacture independent evidence from
already-contaminated data.

**Key argument**: Coverage evidence has genuine value — it is not worthless
simply because it is not independent. If an exhaustive scan (50K+ configs across
N deterministic sessions) converges on the same family that human-guided V4–V8
found, this is strong **confirmatory** evidence. It validates that the online
process was not biased toward an inferior family by limited search. But
confirmatory evidence ≠ independent evidence. The finding correctly insists on
this distinction to prevent the overclaim path: "x38 confirmed the winner" when
in fact x38 only confirmed the coverage.

**However**, F-22's open question about the surprise-divergence case (exhaustive
scan does NOT find the same family) deserves more attention than the finding gives
it. This case is architecturally more significant than convergence, because:

1. **It would be genuinely new evidence**: If a procedurally-blind exhaustive
   scan finds a DIFFERENT family leader than V4-V8's human-guided sessions, this
   is the strongest possible signal that the online process was biased — either
   by contamination, by search space limitation, or by implicit structural priors
   accumulated across V4→V8.

2. **It does NOT automatically invalidate the old winner**: The new family leader
   might be a result of objective function differences, cost assumptions, or
   search space configuration. The divergence is a **diagnostic alarm**, not an
   automatic override.

3. **It requires a specific protocol**: The framework should not silently absorb
   this divergence into a "let the convergence analysis handle it" bucket. It
   needs an explicit divergence investigation that:
   - Surfaces the finding prominently (not buried in session logs)
   - Compares the two families on matched objectives and cost scenarios
   - Records whether the divergence is due to search bias, objective
     differences, or genuine alternative
   - Escalates to human researcher for judgment (this cannot be auto-resolved)

For the first open question — whether coverage confirmation changes the campaign
verdict — my position is: **No**. The verdict stays `INTERNAL_ROBUST_CANDIDATE`.
Coverage confirmation is metadata, not verdict elevation. Adding a
`coverage_status` field (enum: `pending`, `confirmed_same_family`,
`diverged_new_leader`, `partial`) to the verdict metadata cleanly separates the
diagnostic value from the claim level. This aligns with the metadata approach
proposed for F-20's `convergence_level`.

**Proposed amendment**: Accept the 3-type evidence classification. Add:
1. Explicit surprise-divergence protocol for the case where exhaustive scan
   contradicts online lineage (diagnostic alarm → matched comparison → human
   judgment)
2. `coverage_status` metadata field on campaign verdicts to record Phase 1
   results without inflating the verdict taxonomy

### Classification: Judgment call

Correct. The evidence taxonomy is clear, but its implications for verdict
metadata and the surprise-divergence protocol involve tradeoffs (simplicity vs.
completeness) where reasonable architects could disagree.

---

## X38-D-25: Regime-aware policy structure — ACCEPT (V8 position, V2+ extension path)

### Position

F-25 asks a precise architectural question: does x38's search space allow a
single frozen policy with explicit regime-aware structure? The evidence
overwhelmingly favors maintaining V8's position for V1.

**Evidence chain**:

1. **V8 protocol** (`RESEARCH_PROMPT_V8.md:469-475` [extra-archive]): FORBIDS
   regime-specific parameter sets in the main scientific search. This prohibition
   was the result of V4→V8's accumulated experience with overfit patterns — it is
   not arbitrary.

2. **V8 layering allowance** (`RESEARCH_PROMPT_V8.md:312` [extra-archive]):
   ALLOWS layered policies IF they pass paired ablation evidence. The nuance:
   regime-aware structure is not absolutely banned — but it must PROVE it adds
   value over the stationary baseline through rigorous paired comparison.

3. **Empirical evidence from btc-spot-dev** [extra-archive]: The pre-existing
   primary candidate (VTREND E5_ema21D1) profits in ALL 6 observed BTC regimes.
   Regime conditioning was explicitly tested in the research lineage and found to
   HURT: "VTREND profits ALL 6 regimes → regime conditioning HURTS"
   (`MEMORY.md` project context; research studies X5, X7 [extra-archive]). On BTC
   at H4 resolution, single stationary policy empirically dominates regime-aware
   alternatives.

4. **Parameter multiplication risk**: A 3-parameter strategy (VTREND) that
   switches between regimes effectively becomes 6+ parameters (3 per regime +
   classifier). This increases selection bias (DSR penalty), reduces WFO power,
   and expands the search space combinatorially — exactly the problems the
   framework is designed to control.

**Key argument**: F-25 correctly identifies two positions. Position 1 (single
stationary policy, regime conditioning forbidden) is supported by V8 lineage,
empirical evidence, and overfit theory. Position 2 (allow regime-aware structure
with strict ablation gates) is a superset that includes Position 1 as a special
case. The question reduces to: does the flexibility of Position 2 justify its
costs in V1?

My answer: **No, not in V1.** Three reasons:

- **No empirical demand**: Zero evidence in the project supports regime-aware
  policies on BTC. Every regime-aware attempt (X5, X7, X31-A [extra-archive])
  was rejected because it destroyed the fat-tail alpha concentration that drives
  VTREND's returns.

- **Ablation gate complexity**: Specifying a rigorous ablation gate for
  regime-aware structures is a non-trivial design task. What constitutes
  sufficient paired evidence? Minimum exposure per regime? Minimum regime count?
  These questions require empirical calibration that V1 does not have —
  especially if V2+ introduces multi-asset data where regime structure may differ.

- **V8 precedent is earned, not assumed**: The V8 prohibition was the product of
  5 governance iterations. Overriding it without new contradictory evidence
  violates rules.md §5 (burden on proposer of change).

**However**, permanently closing the door on regime-aware policies would be
over-conservative. Multi-asset campaigns (V2+) may encounter asset classes where
regime heterogeneity is genuinely stronger than BTC's relatively monotonic
trend-following alpha. The design should preserve an explicit extension path.

**Sub-question — regime classifier ownership**: The finding asks whether the
regime classifier is part of the policy (frozen at freeze time) or an external
framework input. This is architecturally important. My position: **internal to
the policy.** Evidence: E5_ema21D1's D1 EMA(21) regime filter is a strategy
component, frozen at freeze time, validated as part of the strategy's parameter
set. If regime classifiers were external (framework-provided), they would create
a hidden dependency: changing the classifier post-freeze changes strategy
behavior without the strategy "knowing." This breaks the immutability guarantee
that the contamination firewall (topic 002) requires. An external classifier also
violates session independence — all sessions would see the same
framework-provided regime labels, creating a shared information channel.

**Proposed amendment**:

1. **V1 spec**: single stationary policy is the only allowed structure in the
   search space. Regime-specific parameter sets are forbidden per V8 lineage.
   Layered components (e.g., D1 EMA regime filter) are allowed as INTERNAL
   strategy components if they pass ablation gates — but they are part of the
   frozen policy, not regime-switching logic.

2. **V2+ extension path**: regime-aware policy structure is a declared extension
   point. Activation requires: (a) empirical evidence from a campaign where
   stationary policy fails, (b) specification of paired ablation gates, (c) human
   researcher approval per governance protocol.

3. **Classifier ownership invariant**: regime classifiers, if allowed in V2+,
   MUST be internal to the policy (frozen at freeze time). External
   framework-provided classifiers are forbidden because they break immutability
   and session independence.

### Classification: Judgment call

Correct. Both positions have merit — the tradeoff is flexibility vs. overfit
protection. Evidence favors the conservative position for V1, with an explicit
V2+ extension path. The classifier-ownership question is a design invariant that
should be frozen now regardless of V1/V2+ timing.

---

## Summary

### Accepted (near-convergence candidates)

All 4 findings are **accepted in substance**. Core diagnoses are correct and
well-evidenced:

- **X38-D-01**: Philosophy correct. Amendment: formalize two-level structure
  (mission aspiration vs. operational promise) and enforcement dependency chain.
- **X38-D-20**: 3-tier model correct. Naming accepted
  (Mission/Campaign/Certification). Convergence metadata proposed instead of
  verdict sub-states.
- **X38-D-22**: Evidence taxonomy correct. Amendment: surprise-divergence
  protocol and coverage_status metadata.
- **X38-D-25**: V8 position correct for V1. Amendment: explicit V2+ extension
  path and classifier-ownership invariant.

### Challenged (need debate)

Challenges are on **arguments and amendments**, not on conclusions:

- **X38-D-01 ↔ X38-D-20 merge**: Should F-01's two-level formalization be
  absorbed into F-20's three-tier model, making F-01 a philosophical preamble
  rather than a standalone architectural decision?
- **X38-D-20 metadata design**: Convergence metadata vs. verdict sub-states — is
  the metadata approach sufficient, or does the verdict name itself need to carry
  convergence information for safety?
- **X38-D-22 divergence protocol**: How much protocol machinery for the
  surprise-divergence case? Is a simple diagnostic alarm sufficient, or does the
  framework need a full investigation protocol?
- **X38-D-25 V2+ boundary**: How explicit should the V2+ extension path be in
  the V1 spec? A vague "V2+ may allow this" vs. a concrete gate specification
  that V2+ must satisfy.

---

## Cross-topic tensions

Per rules.md §21 (transition: topic opened before 2026-03-23, adding section at
first debate round):

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 001 (campaign-model) | X38-D-03 | F-01 constrains campaign stop conditions: `NO_ROBUST_IMPROVEMENT` must be a valid campaign exit, not a failure | 001 owns decision; 007 provides constraint |
| 002 (contamination-firewall) | X38-D-04 | C-10: F-01 operationalization depends on firewall enforcing "inherit methodology not answers." Firewall must block answer priors per F-01 | 002 owns decision; 007 provides constraint |
| 003 (protocol-engine) | X38-D-05 | F-25 regime prohibition constrains protocol stage design: no regime-switching stages in V1 pipeline | 003 owns decision; 007 provides constraint |
| 004 (meta-knowledge) | MK-17 | MK-17 shadow-only is prerequisite for F-01 operational interpretation. Already CLOSED — invariant frozen | shared — see C-02 |
| 010 (clean-oos-certification) | X38-D-12, X38-D-21 | F-22 evidence taxonomy defines Phase 1 vs. Certification boundary. F-20 verdict taxonomy constrains certification verdicts | 010 owns decision; 007 provides taxonomy |

---

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-D-01 | Triết lý: kế thừa methodology, không đáp án. Two-level formalization + enforcement dependency proposed | Judgment call | Open | — | — |
| X38-D-20 | 3-tier claim: Mission / Campaign / Certification. Naming accepted, convergence metadata proposed | Thiếu sót | Open | — | — |
| X38-D-22 | Phase 1 evidence classification. Taxonomy accepted, surprise-divergence protocol proposed | Judgment call | Open | — | — |
| X38-D-25 | Regime-aware policy: V1 single stationary, V2+ extension, classifier-internal invariant | Judgment call | Open | — | — |
