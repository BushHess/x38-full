# Findings Under Review — Discovery Foundations

**Topic ID**: X38-T-19A
**Opened**: 2026-04-02
**Author**: human researcher

3 foundational findings about the discovery loop's boundaries — extracted from
Topic 019 (18 findings, 3005 lines) which was too large for effective debate.
These define the contamination boundary, code authoring mechanism, and data
scope that all other 019 sub-topics depend on.

**Origin**: Split from Topic 019 (2026-04-02). Findings copied verbatim.

**Issue ID prefix**: `X38-DFL-` (Discovery Feedback Loop).

**Convergence notes applicable** (full text at `../000-framework-proposal/findings-under-review.md`):
- C-01: MK-17 != primary evidence; firewall = main pillar
- C-02: Shadow-only principle settled
- C-12: Answer priors banned ALWAYS

**Closed topic invariants** (non-negotiable):
- Topic 018 SSE-D-02: Bounded ideation = results-blind, compile-only, OHLCV-only, provenance-tracked
- Topic 018 SSE-D-11: APE v1 = template parameterization only, no code generation
- Topic 018 SSE-D-05: Recognition stack = pre-freeze topology + named working minimum inventory (Judgment call)
- Topic 002 F-04: Contamination firewall typed schema + whitelist
- Topic 004 MK-17: Same-dataset empirical priors = shadow-only
- Topic 007 F-01: "Inherit methodology, not answers"

---

## DFL-04: Contamination Boundary for the Discovery Loop

- **issue_id**: X38-DFL-04
- **classification**: Thiếu sót
- **opened_at**: 2026-03-29
- **opened_in_round**: 0
- **current_status**: Open

**Motivation**:

The discovery loop introduces a new information flow that the contamination
firewall (Topic 002) was not designed for:

```
Pipeline Results + Raw Data --> [AI Analysis] --> [Report] --> [Human]
        ^                                                        |
        |                                                   [Deliberation]
        |                                                   Human ↔ AI
        |                                                        |
        |                                                   [Convergence]
        |                                                        |
        |                                                   [AI writes code]
        |                                                        |
        |______________________[Validation Pipeline]_____________|
```

This is a FEEDBACK LOOP through the contamination firewall. The firewall's
current model assumes a DAG (directed acyclic graph) — information flows forward
through pipeline stages, never backward. The discovery loop breaks this
assumption by feeding output information back as input.

**Proposal**: Formal contamination model for the discovery loop.

**Information classification at each stage**:

| Stage | What flows | Contamination class | Rule |
|-------|-----------|-------------------|------|
| Pipeline --> AI Analysis | Raw metrics, trades, equity curves | Results (forbidden in ideation) | AI analysis layer is EXEMPT from results-blind (it's analysis, not ideation) |
| AI Analysis --> Human | Structured findings (DFL-02 contract) | Process observations (F-22 Type 1) | Classified as coverage/process evidence, NOT answer priors |
| Human --> New Template | Strategy specification | Human-originated, provenance-tracked | NOT results-blind (DFL-03 exception). Provenance records which report informed the decision |
| Human --> Grammar Extension | New grammar primitives | Must pass results-blind test | Primitives must be defensible WITHOUT reference to specific results |
| Human ↔ AI Deliberation | Design discussion, feasibility, tradeoffs | Results-aware (analysis, not ideation) | Deliberation CAN reference results. Convergence required before code (DFL-05) |
| Convergence --> Code | AI writes strategy code | Provenance-tracked (links to deliberation) | Human-initiated, convergence-gated. NOT automated gen (SSE-D-11 distinction) |
| Code --> Pipeline | Strategy implementation | Normal pipeline input | Subject to all existing validation gates |

**Firewall interaction model**:

The discovery loop does NOT violate the contamination firewall because:
1. **No automated feedback**: AI analysis never directly modifies the pipeline.
   Human is always the gateway.
2. **No answer priors**: Analysis outputs are process observations ("strategy X
   has unusual MDD pattern"), not answer priors ("use parameter Y=120").
3. **Provenance tracked**: Every human-originated template records its lineage
   back to the DFL report that inspired it.
4. **Validation still applies**: Templates from the discovery loop pass through
   the same validation pipeline as any other candidate.

**What the firewall DOES block**:
- AI analysis directly generating strategy code (SSE-D-11 violation)
- AI analysis directly modifying grammar (SSE-D-02 violation)
- Human feedback that encodes specific parameter values from results
  ("set lookback=120 because that's what worked" = answer prior)

**Open questions**:
- Is human-mediated feedback fundamentally different from automated feedback
  for contamination purposes? Or is it "contamination laundering"?
- How to verify that human-provided grammar extensions are truly results-blind
  (not just the human encoding results knowledge into abstract-sounding primitives)?
- Should the contamination firewall be extended with a new category for
  "discovery loop observations"? Or do existing F-04 categories suffice?
- Does the analysis layer's memory (past reports) constitute a contamination
  risk for future analyses?

---

## DFL-05: Deliberation-Gated Code Authoring

- **issue_id**: X38-DFL-05
- **classification**: Judgment call
- **opened_at**: 2026-03-29
- **opened_in_round**: 0
- **current_status**: Open

**Motivation**:

DFL-01 through DFL-04 bridge "data → insight" but NOT "insight → running code →
validated strategy." Every algorithm in btc-spot-dev required novel code:

- VDO: `vdo_threshold` filter logic in strategy.py
- EMA(21d) regime: D1 EMA cross-detection in `on_init` + `on_bar`
- E5 exit: EMA cross-down exit mechanism replacing ATR trail-only

None could be produced by "template parameterization" (SSE-D-11). They required
designing indicator logic, writing Python, integrating with Strategy ABC
(`on_init`, `on_bar`, `on_after_fill`), creating configs, and running backtests.

**The actual practice that produced all project alpha**:

```
Human sends prompt/question to AI
         |
AI and human discuss: feasibility, design, tradeoffs
         |
Discussion continues — multiple rounds if needed
         |
Convergence: both sides agree on WHAT to build and WHY
         |
AI writes code (only after convergence)
         |
Code enters normal validation pipeline
```

This is how VDO, E5, EMA(21d) regime, and every X12-X32 study were created.
The pattern is: **deliberation first, code second.** AI never speculatively
generates strategy code — it writes code only after sufficient discussion
establishes that the approach is sound.

**Proposal**: Formalize this as "Deliberation-Gated Code Authoring" — a
code-writing mechanism gated on convergence of human-AI deliberation.

**Key properties**:

| Property | Value | Rationale |
|----------|-------|-----------|
| Initiator | Human always | Human decides what to investigate |
| Deliberation | Human <-> AI, multiple rounds | Ensures approach is sound before coding |
| Convergence gate | Both sides agree on what + why | Prevents speculative code generation |
| Code author | AI (after convergence) | AI can write code, human reviews |
| Code review | Human approves/modifies | Human is final authority on code |
| Validation | Normal pipeline (all gates) | No special treatment for discovery loop code |
| Provenance | Links to deliberation artifact | Traceable: which discussion produced this code |

**Relationship to SSE-D-11**:

SSE-D-11 says "APE v1 = template parameterization only, no free-form code
generation." DFL-05 proposes a DIFFERENT mechanism:

| Aspect | APE (SSE-D-11) | DFL-05 |
|--------|----------------|--------|
| Trigger | Automated (grammar enumeration) | Human-initiated |
| Input | Template + parameter ranges | Deliberation conclusions |
| Process | Mechanical fill-in | Discussion -> convergence -> writing |
| Gate | None (auto-generates) | Convergence of deliberation |
| Human role | None | Initiator, participant, reviewer |
| Output | Parameterized variant | Novel code (new indicators, signals, exits) |

DFL-05 is NOT an exception to SSE-D-11. It is a SEPARATE mechanism:
- SSE-D-11 governs AUTOMATED code generation (banned in v1)
- DFL-05 governs HUMAN-INITIATED, DELIBERATION-GATED code authoring

The distinction: automated generation has no quality gate except compilation.
Deliberation-gated authoring has convergence as a quality gate — code is only
written when the approach has been argued to be sound.

**Contamination properties**:

| Stage | What flows | Contamination class |
|-------|-----------|-------------------|
| Human -> AI prompt | Investigation question | No contamination (meta-level) |
| Deliberation | Results, data, analysis, arguments | Results-aware (analysis, not ideation) |
| Convergence -> code | Design conclusions | Provenance-tracked |
| Code -> pipeline | Strategy implementation | Normal pipeline input (all gates apply) |

Deliberation CAN and SHOULD reference results — that's the whole point.
The contamination boundary is:
- Code is provenance-tracked (which deliberation produced it)
- Code enters normal validation (no shortcut)
- Human approved the code before submission

**Open questions**:
- What constitutes "sufficient convergence" for code authoring? Formal criteria
  or human judgment?
- Must deliberation be recorded as a persistent artifact? (Provenance tracking
  suggests yes)
- Can AI suggest code modifications during validation feedback loops? (e.g.,
  "validation failed because X, try changing Y" — is this a new deliberation
  or continuation?)
- Should there be a minimum deliberation depth (e.g., at least N exchanges)
  before code is permitted?
- How does this interact with DFL-03 "grammar extension"? Does a new grammar
  primitive require deliberation before it can be added?

---

## DFL-09: SSE-D-02 Scope Clarification for Systematic Scan

- **issue_id**: X38-DFL-09
- **classification**: Thiếu sót
- **opened_at**: 2026-03-31
- **opened_in_round**: 0
- **current_status**: Open

**Motivation**:

SSE-D-02 (Topic 018, CLOSED) establishes 4 hard rules for bounded ideation.
Hard rule 3 states: **OHLCV-only** — only OHLCV + volume data as input.

DFL-06 proposes systematic exploration of ALL 13 data fields, including
`quote_volume`, `num_trades`, `taker_buy_base_vol`, `taker_buy_quote_vol` —
fields that go beyond OHLCV.

This creates an apparent conflict: DFL-06 needs to scan all available data
to discover unknown patterns. SSE-D-02 restricts input to OHLCV-only.

**The conflict is resolvable** because SSE-D-02 applies to **bounded ideation**
(automated candidate generation), NOT to **analysis** (pattern observation).
But this distinction is implicit, not explicit. Without a formal ruling, a
future agent could reasonably interpret SSE-D-02 as blocking DFL-06's
analyses that use non-OHLCV fields (Analysis 1: microstructure derived from
num_trades/quote_volume/taker_buy_quote_vol; Analysis 5: num_trades vs
volume divergence; Analysis 9: post-VDO-cross events using taker_buy_ratio).

**Proposal**: Explicit scope clarification for SSE-D-02 hard rule 3.

### Scope boundary

| Activity | SSE-D-02 applies? | Rationale |
|----------|-------------------|-----------|
| `grammar_depth1_seed` generation | **YES** — OHLCV-only | Automated ideation. Hard rule 3 in full force |
| `registry_only` generation | **YES** — OHLCV-only | Automated ideation from registry. Same rule |
| APE template parameterization | **YES** — OHLCV-only | Automated (SSE-D-11). Same rule |
| DFL-06 systematic scan (Phase 1-2) | **NO** — all 13 fields | Analysis, not ideation. Results-aware per DFL-04 |
| DFL-01 AI analysis layer | **NO** — all available data | Analysis, not ideation. Exempt per DFL-01 definition |
| DFL-05 deliberation-gated code | **NO** — human decides inputs | Human-initiated, convergence-gated. Separate mechanism per DFL-05 |
| Human-originated templates | **NO** — human decides inputs | DFL-03 deliberate exception (provenance-tracked) |

### Key distinction: ideation vs analysis

SSE-D-02 was designed to prevent **automated candidate generation** from using
data that could introduce contamination through overfitting to complex features.
The concern: if grammar enumeration can use 13 fields x unlimited derived
features, the combinatorial search space explodes and the probability of
spurious candidates increases.

DFL-06's systematic scan is a fundamentally different activity:
- **Purpose**: discover patterns for HUMAN evaluation, not generate candidates
- **Output**: statistical reports (process observations per DFL-04), not strategy code
- **Gate**: human decides what to do with findings (Stage 3 of DFL-08)
- **Contamination**: classified as Type 1 evidence (F-22), not answer priors

The OHLCV-only rule solves a COMBINATORIAL problem (search space explosion in
automated generation). DFL-06 does not have this problem because it does not
generate candidates — it observes data and reports to humans.

### What this does NOT change

- SSE-D-02 hard rules remain fully in force for all automated ideation
- Grammar primitives derived from DFL-06 discoveries MUST satisfy BOTH:
  - Results-blind (SSE-D-02 rule 1): defensible without reference to specific results
  - OHLCV-only (SSE-D-02 rule 3): expressible using only OHLCV fields, even if
    discovered via non-OHLCV analysis (e.g., a non-OHLCV feature like `num_trades`
    cannot become a grammar primitive — it can only enter via human template)
- No new data sources introduced — DFL-06 uses only existing CSV fields
- DFL-04 contamination boundary unchanged

### Implication for grammar extensions

If DFL-06 discovers that `num_trades` (non-OHLCV) is predictive, the
graduation path (DFL-08) handles this:

1. **As human template** (DFL-03 channel 1): human can create a template
   using `num_trades` directly. Provenance-tracked, not results-blind.
   The strategy enters normal validation.

2. **As grammar extension** (DFL-03 channel 2): the grammar primitive
   MUST be expressible in OHLCV-only terms OR the OHLCV-only constraint
   must be formally relaxed for grammar (which would require reopening
   Topic 018 — a high bar). In practice, this means non-OHLCV features
   enter via human templates, not grammar.

This asymmetry is intentional: human templates have human judgment as quality
gate (Tier 3). Grammar extensions have only combinatorial enumeration — hence
the stricter OHLCV-only constraint.

**Cross-topic dependency**: This finding interprets a CLOSED topic (018)
decision. If debate concludes that the interpretation is wrong (SSE-D-02
WAS intended to block DFL-06 scans), then either:
- DFL-06 Analyses 1, 5, 9 must be restricted to OHLCV-only fields, OR
- Topic 018 must be reopened to amend SSE-D-02 (high bar per x38_RULES.md)

**Open questions**:
- Is this scope clarification correct? Or did SSE-D-02 intend to restrict
  ALL framework activities (including analysis) to OHLCV-only?
- If grammar extensions cannot use non-OHLCV features, does this create a
  two-class system where human-template features are richer than grammar
  features? Is that acceptable or does it undermine grammar's purpose?
- Should the clarification be recorded as an amendment to Topic 018's
  final-resolution.md, or is a Topic 019 finding sufficient?

---

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 018 | SSE-D-02 (rule 1) | Bounded ideation results-blind vs discovery loop results-aware | DFL-04 defines contamination boundary |
| 018 | SSE-D-02 (rule 3) | OHLCV-only rule vs DFL-06 scan using all 13 fields — analysis != ideation | DFL-09 proposes scope clarification: SSE-D-02 applies to automated ideation only |
| 018 | SSE-D-11 | APE v1 no code gen. DFL-05 proposes deliberation-gated code authoring as SEPARATE mechanism | DFL-05 defines scope boundary: automated gen (SSE-D-11) vs deliberation-gated authoring (DFL-05) |
| 002 | F-04 | Firewall typed schema — analysis outputs need classification | DFL-04 classifies all analysis outputs as process observations |

---

## Decision summary — what debate must resolve

019A owns only the 3 Tier 1 (foundational) decisions. All other 019 decisions
are downstream and owned by sub-topics 019B-019F.

**Tier 1 — Foundational (resolve first)**:

| ID | Decision | Finding | Alternatives |
|----|----------|---------|-------------|
| D-01 | Is DFL-06/07 analysis a DIFFERENT activity from SSE-D-02 ideation? | DFL-09 | YES (analysis exempt from OHLCV-only) / NO (analysis also restricted) |
| D-02 | Is human-mediated feedback "contamination laundering" or fundamentally different from automated feedback? | DFL-04 | Different (process observations) / Same (contamination) |
| D-03 | Is deliberation-gated code authoring a SEPARATE mechanism from APE (SSE-D-11) or an exception? | DFL-05 | Separate (both exist) / Exception (requires v2+ gate) |

---

## Summary table

| Issue ID | Finding | Classification | Status |
|----------|---------|---------------|--------|
| X38-DFL-04 | Contamination boundary for the discovery loop | Thiếu sót | Open |
| X38-DFL-05 | Deliberation-gated code authoring | Judgment call | Open |
| X38-DFL-09 | SSE-D-02 scope clarification for systematic scan | Thiếu sót | Open |
