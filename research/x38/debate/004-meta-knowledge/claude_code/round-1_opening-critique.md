# Round 1 — Opening Critique: Meta-Knowledge Governance

**Topic**: 004 — Meta-Knowledge Governance
**Author**: claude_code
**Date**: 2026-03-21
**Scope**: Stage 1A — MK-01 through MK-07 + critiques C1, C2
**Input documents**:
- `findings-under-review.md` (17 findings, 15 Open, 2 pre-resolved)
- `input_solution_proposal.md` (Policy Object Model proposal)
- `input_proposal_critique.md` (6 critiques C1–C6)

---

## Preamble

This opening critique synthesizes argued positions on MK-01→MK-07 and
strengthens/challenges critiques C1 and C2. My role: original architect who
designed the initial taxonomy. I will attack weaknesses in my own proposals
where warranted. Per rules.md §5, burden of proof is on the proposer —
I must defend these proposals against the strongest objections.

**MK-17 context**: Same-dataset empirical priors are shadow-only pre-freeze
(RESOLVED 2026-03-19). This simplifies many issues for V1 but does NOT
eliminate the need for correct architecture — V2+ activates empirical priors
on new datasets, and the architecture must support both modes.

---

## MK-01: Maturity Pipeline — ACCEPT observation, REJECT mechanism

### Position

The maturity pipeline observation is empirically correct and well-documented.
V6→V7→V8 shows clear evidence of lesson absorption:

- V6: 8 meta-knowledge lessons, 447-line protocol
- V7: 4 NEW lessons (V6's 8 absorbed), 586-line protocol
- V8: 5 NEW lessons (V7's 4 absorbed), 643-line protocol

Evidence: `RESEARCH_PROMPT_V6.md` lines 436–448 [extra-archive], `RESEARCH_PROMPT_V7.md`
lines 579–587 [extra-archive], `RESEARCH_PROMPT_V8.md` lines 635–644 [extra-archive].

**However**, the finding correctly identifies that this is a _de facto_ mechanism,
not an intentional design. Alpha-Lab must NOT replicate implicit absorption.
Every rule transition must be:

1. **Explicit**: logged with timestamp, source campaign, and justification
2. **Reversible**: retired rules archived, not deleted
3. **Auditable**: a third party can trace why any active rule exists

The analogy "bug report → known issue → permanent fix" (MK-01) is misleading
for Alpha-Lab. In software engineering, a permanent fix is verified by tests.
In research governance, a "permanent fix" (absorbed rule) may be WRONG for a
new context — and there is no automated test for epistemological correctness.

**Proposed design principle**: Alpha-Lab rules NEVER absorb silently. A rule
either (a) remains in its current tier with its metadata, or (b) is explicitly
promoted/demoted/retired with a logged reason. No "maturity pipeline" that
erases provenance.

### Classification: Thiếu sót

The current design (V4→V8 implicit absorption) is not available as a
mechanism in Alpha-Lab (offline pipeline has no protocol body to absorb into).
But the PATTERN must be explicitly prevented — otherwise it re-emerges as
config drift or knowledge-file accumulation without governance.

---

## MK-02: Five Harms — ACCEPT all, prioritize differently

### Position

All five harms are real. But they are not equally important for Alpha-Lab:

| Harm | Severity for Alpha-Lab | Reasoning |
|------|----------------------|-----------|
| #1 Provenance loss | **HIGH** | Reproducibility is Alpha-Lab's core promise. Losing "why" undermines audit. |
| #2 Protocol bloat | **MEDIUM** | Offline pipeline tolerates more rules than AI context window. But compliance cost still exists in code complexity. |
| #3 Implicit data leakage | **CRITICAL** | Irreducible (MK-03). Alpha-Lab's entire contamination architecture exists to bound this harm. |
| #4 No unwind | **HIGH** | Same-dataset shadow-only (MK-17) defers this for V1. But V2+ needs explicit unwind. |
| #5 Diminishing returns | **MEDIUM** | Real but addressable: bounded by Tier 2 expiry + active cap. |

**Key argument on Harm #3**: The finding says "information laundering: data-specific
lessons become universal-looking rules." This is precisely correct. Evidence:

- V8 line 539: "a transported slower-state clone may not be the final leader
  without incremental paired evidence" — sounds like universal statistics, but
  conviction comes from V4/V5 D1-EMA-on-H4 experience on BTC/USDT.
- V8 lines 186–201: "14 quarterly folds" — looks like protocol design, but
  reflects BTC-specific discovery window.

Both examples show the SAME failure mode: a lesson derived from specific data,
phrased as universal methodology, embedded in protocol without provenance.

**However**, I must challenge MK-02's framing on Harm #5. The finding says
"marginal value of each new constraint decreases while compliance cost
increases linearly." This assumes compliance cost is linear. In an offline
pipeline, compliance cost is STEP-FUNCTION: a new rule either requires a new
code check (one-time cost) or it doesn't (zero cost). Protocol bloat in code
is qualitatively different from protocol bloat in a prompt document that an AI
must hold in context.

**Proposed amendment to Harm #5**: For Alpha-Lab, the real risk is not
"protocol bloat slows research" but "conflicting rules create impossible
compliance" (Harm #5 → precondition for MK-11). Reframe: the danger is
CONTRADICTION, not LENGTH.

### Classification: Sai thiết kế (for Harm #3); Thiếu sót (for Harms #1, #2, #4, #5)

---

## MK-03: Fundamental Constraint — ACCEPT, refine operating point

### Position

The learning-vs-independence tradeoff is correctly identified as irreducible.
MK-17's resolution (shadow-only on same dataset) correctly positions Alpha-Lab
near the independence end for same-data campaigns. I accept this.

**But the finding under-specifies the operating point model.** MK-03 implies
a single point on a curve. In reality, Alpha-Lab needs a CONTEXT-DEPENDENT
operating point:

| Context | Operating point | Rationale |
|---------|----------------|-----------|
| Same dataset, same asset | Near-independence (shadow-only, MK-17) | Contamination risk maximal |
| New dataset, same asset | Moderate learning (Tier 2 active with full metadata) | New eval data can test priors |
| New asset, same data surface | Moderate-high learning (Tier 2 active, scope-matched) | Different asset may invalidate, but data surface similar |
| New asset, new data surface | Full learning (Tier 2 active, challenge triggers mandatory) | Fundamentally new context |

The V4→V8 evidence supports this: 5 sessions on same BTC/USDT data with
increasing meta-knowledge produced 5 different winners
(`CONVERGENCE_STATUS_V3.md` [extra-archive]). More meta-knowledge did not force convergence —
suggesting the same-dataset operating point should be near independence. But
this does NOT prove that meta-knowledge is valueless on new datasets.

**Proposed design principle**: The operating point is a function of
`(dataset_overlap, asset_overlap, data_surface_overlap)`, not a global
constant. Shadow-only is one end of the continuum, not the only mode.

### Classification: Judgment call

The optimal operating point per context is a design judgment. MK-17 resolved
the same-dataset case. The new-dataset cases remain open and should be
deferred to V2+ design (consistent with solution proposal §13).

---

## MK-04: Derivation Test — ACCEPT concept, CHALLENGE operationality

### Position

The derivation test is the RIGHT conceptual tool. Its question is well-posed:

> "Can a researcher who has never seen any backtest results on any data
> derive this rule from mathematics, statistics, logic, or experimental
> design first principles alone?"

The examples in the finding are illuminating. "No lookahead" = clearly Yes.
"14 quarterly folds" = clearly No. These extremes work.

**But the test FAILS at the boundary that matters most.** The "Partially"
category is where ALL the important Tier 2 rules live, and it is inherently
subjective:

**Example 1**: "Transported clone needs incremental proof" (V8 line 539).
- Derivable argument: redundancy principle — if feature B is a linear
  transformation of feature A, adding B cannot provide orthogonal information.
  This IS derivable from basic statistics.
- Data-derived argument: but the EMPHASIS and specificity (specifically
  "transported slower-state clone") comes from V4/V5 where D1 EMA transported
  to H4 appeared good but merely restated D1 information.
- Verdict: different researchers would classify this differently. The
  first-principles basis is there but the CONVICTION is data-amplified.

**Example 2**: "Layering is a hypothesis, not a default."
- Derivable argument: Occam's razor / MDL principle — prefer simpler models
  absent evidence.
- Data-derived argument: but the STRENGTH of this prior (it became a binding
  rule, not a suggestion) comes from BTC/USDT V4 rounds where multi-layer
  consistently failed.
- Verdict: the principle is derivable but the FORCE (how much it constrains
  search) is entirely data-derived.

**The key insight**: the derivation test classifies the EXISTENCE of a rule
reasonably well, but cannot classify the FORCE of a rule. A rule can be
derivable in principle but carry data-derived force. This distinction is
critical for Alpha-Lab because force determines how much a rule constrains
search.

**This connects to C1** (critique): the proposal's "policy compiler" claims
to run derivation tests deterministically. It cannot. The test requires
JUDGMENT about whether a rule's force is proportionate to its first-principles
basis. No code can make this judgment.

**Proposed refinement**: Split the derivation test into two questions:
1. **Existence test** (automatable): Does this rule have ANY first-principles
   basis? YES/NO. If NO → reject (pure data-derived).
2. **Force calibration** (human-required): Is the rule's constraining force
   proportionate to its first-principles basis, or does it carry excess force
   from data-specific conviction? This determines tier placement and metadata
   requirements.

### Classification: Thiếu sót

The derivation test as currently specified conflates existence and force.
Refining into two questions makes it more operational while preserving the
core insight.

---

## MK-05: 3-Tier Rule Taxonomy — ACCEPT architecture, CHALLENGE Tier 2 breadth

### Position

The three-tier architecture is sound. The harm-mitigation table in MK-05 is
correct — each harm maps to a mitigation mechanism:

| Harm | Mitigation |
|------|-----------|
| #1 Provenance loss | Tier 2 provenance block |
| #2 Protocol bloat | Tier 2 expiry, Tier 3 non-accumulating |
| #3 Implicit leakage | Tier 2 leakage grade + challengeable |
| #4 No unwind | Tier 2 expiry, Tier 3 auto-expires |
| #5 Diminishing returns | Tier 2 expiry bounds steady-state size |

**3 tiers is the right number.** Arguments:

- 2 tiers (axiom / everything-else) loses the critical distinction between
  structural priors and session-specific rules.
- 4 tiers (e.g., splitting Tier 2 into "strong prior" and "weak prior") adds
  classification overhead without clear operational benefit — the metadata
  (leakage grade, confidence state) already captures this gradient.

**However, Tier 2 spans too wide a range.** Currently Tier 2 includes:

- "Transported clone needs incremental proof" — almost an axiom, strong
  first-principles basis, light data confirmation
- "Vol-clustering features perform better in bear markets on BTC" — almost
  session-specific, weak first-principles basis, strong data origin

Both are classified Tier 2, but they should carry VERY different governance
weight. The solution proposal's metadata (leakage grade LOW/MODERATE/HIGH)
partially addresses this, but:

**Concern**: The leakage grade is itself a judgment call (who assigns it?
how? — back to C1/C2 problems). And in V1 with MK-17 shadow-only, ALL
empirical rules are shadow regardless of leakage grade, so the grade is
inert.

**Proposed position**: For V1, Tier 2 is a single bucket — all shadow on
same dataset. The leakage grade field EXISTS in the schema but is not used
for any runtime decision in V1. For V2+, the leakage grade becomes
operational and the wide Tier 2 range becomes a real issue that needs
sub-classification or graduated force.

### Classification: Thiếu sót

The taxonomy is correct in structure. The Tier 2 breadth issue is real but
can be deferred to V2+ because MK-17 shadow-only makes it inert for V1.

---

## MK-06: Three Types of Leakage — ACCEPT, CHALLENGE boundary

### Position

The three-way distinction (parameter / structural / attention) is a genuine
contribution. It replaces the binary "meta-knowledge vs data-derived" with a
more nuanced model that maps directly to enforcement mechanisms:

| Type | Enforcement |
|------|------------|
| Parameter leakage | Machine-blocked (typed schema, no values in rules) |
| Structural leakage | Bounded (Tier 2 metadata, shadow-only V1) |
| Attention leakage | Accepted (unavoidable, net-positive) |

**This maps cleanly to the contamination firewall** (topic 002):
- Firewall BLOCKS parameter leakage (zero tolerance)
- Firewall GOVERNS structural leakage (Tier 2 metadata)
- Firewall IGNORES attention leakage (not contamination)

**However, the boundary between structural and attention leakage is
operationally blurry.** Consider:

**Example A**: "Check cross-timeframe alignment carefully"
- MK-06 classifies this as attention leakage (where to look)
- But IF this lesson arose because V6 found that cross-timeframe features
  had 2x higher hit rate than same-timeframe features on BTC, then following
  this guidance causes the researcher to WEIGHT cross-timeframe features
  more heavily — which narrows search in the same way a structural prior does.

**Example B**: "Multi-layer architectures deserve extra scrutiny"
- Sounds like structural leakage (architecture prior)
- But all it actually DOES is make the researcher look more carefully at
  multi-layer results — which is attention guidance.

The distinction is not about the CONTENT of the lesson but about its EFFECT
on search behavior. The same lesson can be structural or attention depending
on how strongly it's followed.

**Proposed refinement**: Instead of classifying lessons into three types
(which requires judging effect, not just content), classify the ENFORCEMENT
MECHANISM:

1. **Schema-blocked**: values, thresholds, identities → zero tolerance
2. **Metadata-governed**: rules with tier, scope, expiry, challenge →
   controlled leakage
3. **Unregulated**: everything else → no special handling needed

This is equivalent to MK-06's three types but defined by WHAT THE FRAMEWORK
DOES, not by an epistemological judgment about what the lesson IS. It's
more operational because the framework controls enforcement mechanisms, not
epistemological categories.

### Classification: Thiếu sót

The conceptual model is correct. The refinement makes it more operational
for implementation.

---

## MK-07: Reconciliation with F-06 — ACCEPT, but question necessity

### Position

The two-dimensional filtering model (F-06 categories × 3-tier taxonomy) is
conceptually clean:

```
Lesson arrives → F-06 category check: is the TOPIC allowed?
    → YES → Derivation test: Tier 1, 2, or 3?
    → NO → reject as contamination
```

**But I question whether F-06 categories add operational value beyond the
tier system.** Consider:

F-06 defines 4 whitelist categories:
- PROVENANCE/AUDIT/SERIALIZATION
- SPLIT_HYGIENE
- STOP_DISCIPLINE
- ANTI_PATTERN

The tier system defines governance by epistemological status:
- Tier 1: axiom (derivable)
- Tier 2: structural prior (empirical, governed)
- Tier 3: session-specific (auto-expire)

**Scenario**: A lesson about "feature selection" (not in F-06 categories)
that IS derivable from first principles (Tier 1). Example: "features must
be stationary or cointegrated with the target." This is an axiom about
statistical validity. F-06 would reject it (wrong category). The tier
system would accept it (Tier 1 axiom).

**The F-06 category whitelist is NARROWER than what Alpha-Lab needs.** The
4 categories were designed for the V6→V8 online handoff, where the problem
was AI context contamination. Alpha-Lab's contamination vector is different
(data/knowledge files, not AI memory). Alpha-Lab may need categories that
don't exist in F-06.

**Proposed position**: For V1, drop the F-06 category whitelist as a
separate gate. Instead, use the tier system as the SOLE classifier:

- Tier 1 axioms: allowed by definition (zero leakage)
- Tier 2 structural priors: allowed with metadata (controlled leakage)
- Tier 3 session-specific: scoped to session (no cross-campaign)
- Anything that fails the derivation test AND has no first-principles basis:
  REJECTED (contamination)

F-06 categories can still exist as optional TAGS on rules (for organization
and querying), but they should NOT be a hard gate that blocks valid axioms
because they don't fit a predetermined category list.

**Evidence for this position**: The V8 protocol itself has rules that don't
fit F-06 categories cleanly. "Common daily-return domain for mixed-TF
comparison" (`RESEARCH_PROMPT_V8.md` line 641 [extra-archive]) — this is about STATISTICAL
METHOD, not provenance/audit/split/stop/anti-pattern. Under F-06, it would
need to be classified as ANTI_PATTERN (not doing it is an anti-pattern), but
that's a stretch.

### Classification: Thiếu sót

F-06 and the tier system address different dimensions (as MK-07 correctly
notes), but F-06's category list is too narrow for Alpha-Lab. Merging the
gate into the tier system is simpler and more extensible.

---

## C1 (from critique): Policy Compiler Determinism — STRENGTHEN

### Position

I wrote the original 3-tier proposal. The critique is correct and I
strengthen it here.

The solution proposal (§4) says the policy compiler runs "deterministic
checks" including verifying epistemological status. **This is architecturally
wrong.** The compiler conflates two fundamentally different functions:

| Function | Nature | Can be automated? |
|----------|--------|-------------------|
| Format validation | Mechanical | YES — schema compliance, required fields, type checking |
| Tier classification | Judgment | NO — requires understanding epistemological status |
| Scope validation | Partially | YES for scope ≤ provenance; NO for scope appropriateness |
| Force calibration | Judgment | NO — requires assessing proportionality (MK-04 refinement) |

**The failure mode is specific and dangerous**: An AI writes `basis:
"axiomatic"` for a rule that is actually empirical. The compiler validates
the format (field exists, value is in enum) and accepts it. The rule now has
Tier 1 hard power. No one reviews it because the compiler said "PASS."

**This is worse than no compiler.** Without a compiler, a human would review
every rule. With a false-deterministic compiler, the human trusts the
compiler's PASS and doesn't review.

**Evidence from V4→V8**: The handoff prompt (`PROMPT_FOR_V8_HANDOFF.md` line [extra-archive]
7) says "Transfer only meta-knowledge, NOT data-derived specifics." V8
followed this rule. Yet V8 still contains data-derived rules disguised as
methodology (MK-02, Harm #3). The RULE was followed (the AI believed it was
transferring only methodology), but the JUDGMENT about what counts as
"methodology" was wrong. A deterministic compiler checking "did you follow
the rule?" would have passed V8's handoff — and the data-derived rules would
still have leaked.

**Proposed architecture**:

```
Rule proposal → Format Validator (automated, deterministic)
                    │
                    ▼ (format OK)
               Classification Queue (requires human or adversarial review)
                    │
                    ▼ (tier assigned)
               Scope Validator (automated: scope ≤ provenance)
                    │
                    ▼ (scope OK)
               Active Rule Registry
```

The policy compiler becomes a FORMAT VALIDATOR only. Classification is a
separate HUMAN-GATED step. The solution proposal's "auditor agent" (§4) is
not deterministic — it's judgment by another AI, which leads to C2.

### Classification: Sai thiết kế

Claiming determinism for a judgment task creates a false sense of security.
The compiler must be architecturally separated from classification.

---

## C2 (from critique): Auditor Agent Circularity — ACCEPT, extend

### Position

The critique correctly identifies the circularity: who audits the auditor?
I accept the core argument and extend it.

**The deeper problem**: The solution proposal (§4) sets up an authority
chain: Search AI → Policy Compiler → Auditor Agent → Human. The compiler
validates format (OK, automatable). But the auditor "chỉ downgrade, không
upgrade" — this is still a JUDGMENT about whether a rule deserves its current
tier. The auditor and the proposing AI share the same training distribution.
If the proposing AI has a systematic bias (e.g., classifying empirical rules
as "partially derivable" because its training data conflates correlation with
causation), the auditor will share that bias.

**Adversarial probing (C2's proposed fix) is better but not sufficient.**
It requires one AI to argue AGAINST a rule. This is structurally better than
one AI auditing another AI's classification. But:

1. Both agents may share systematic biases about what counts as "derivable"
2. The adversarial argument is only as good as the counterexample space the
   agent can imagine — and AI may systematically fail to imagine certain
   counterexamples (ones outside its training distribution)
3. Who evaluates which adversarial argument is strong enough to trigger
   human review?

**Proposed resolution for V1**:

Given MK-17 (shadow-only on same dataset), the auditor/adversarial question
is DEFERRED for V1:

- Tier 1 axioms: human researcher classifies at creation (small set, doesn't
  grow fast — V8 has ~15 axiom-level rules after 9 rounds)
- Tier 2/3 on same dataset: shadow-only → classification doesn't matter for
  runtime behavior → human reviews at leisure, not on critical path
- Tier 2 on new dataset (V2+): HERE the auditor question becomes critical

For V2+, I propose:

1. **No dedicated auditor agent.** The adversarial probing model (C2's fix)
   is correct.
2. **ALL Tier 2 promotions require human confirmation.** This is scalable
   because Tier 2 rules accumulate slowly (V4→V8: ~10 Tier 2 rules over 9
   rounds ≈ ~1 per round. At this rate, human review is not a bottleneck).
3. **Adversarial probes are RECORDED, not adjudicated by AI.** The human
   reviewer sees: (a) proposed rule, (b) adversarial counterargument, (c)
   proposer's rebuttal. Human decides.

**Evidence for scalability**: The V4→V8 lineage produced ~15 axiom-level
rules and ~10 structural priors over 9 rounds
(`RESEARCH_PROMPT_V8.md` lines 596–633 [extra-archive] anti-patterns + lines 621–633
re-derivation rules + lines 635–644 meta-knowledge lessons). Even doubling
this rate, human review of ~2-3 rules per campaign is feasible.

### Classification: Thiếu sót

The auditor design is missing a credible authority chain. For V1,
human-gated classification is sufficient. For V2+, adversarial probing +
human confirmation replaces the auditor agent.

---

## Summary of Positions

### Accepted (proposed as near-convergence candidates)

1. **MK-01**: Maturity pipeline is real, Alpha-Lab must prevent implicit
   absorption. Rules never absorb silently.
2. **MK-02**: All five harms are real. Harm #3 is irreducible. Harm #5
   reframed as contradiction risk, not length risk.
3. **MK-05**: 3-tier architecture is correct. Tier 2 breadth deferred to V2+.
4. **MK-06**: Three leakage types accepted, refined to enforcement-mechanism
   classification.

### Challenged (need debate)

1. **MK-03**: Operating point must be context-dependent, not globally fixed.
2. **MK-04**: Derivation test conflates existence and force. Split into two
   questions: existence (automatable) + force calibration (human).
3. **MK-07**: F-06 category whitelist is too narrow. Drop as hard gate, keep
   as optional tags.
4. **C1**: Policy compiler = format validator ONLY. Classification is a
   separate human-gated step.
5. **C2**: No dedicated auditor. Adversarial probing + human confirmation
   for all Tier 2 promotions.

---

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|----------|-------|-----------|------------|---------------------|----------------------|
| X38-MK-01 | Maturity pipeline: observation | Thiếu sót | Open | — | — |
| X38-MK-02 | Five harms of maturity pipeline | Sai thiết kế | Open | — | — |
| X38-MK-03 | Fundamental constraint: learning vs independence | Judgment call | Open | — | — |
| X38-MK-04 | Derivation Test: existence vs force split | Thiếu sót | Open | — | — |
| X38-MK-05 | 3-Tier Rule Taxonomy: architecture + Tier 2 breadth | Thiếu sót | Open | — | — |
| X38-MK-06 | Three leakage types → enforcement-mechanism classification | Thiếu sót | Open | — | — |
| X38-MK-07 | F-06 whitelist: drop as gate, keep as tags | Thiếu sót | Open | — | — |
| C1 | Policy compiler = format validator only | Sai thiết kế | Open | — | — |
| C2 | Auditor agent → adversarial probing + human gate | Thiếu sót | Open | — | — |
