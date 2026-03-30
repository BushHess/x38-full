# Findings Under Review — Discovery Feedback Loop

**Topic ID**: X38-T-19
**Opened**: 2026-03-29
**Author**: human researcher

5 findings about the Human-AI collaborative discovery loop — the mechanism by
which the framework enables creative discovery of new algorithms, as distinct from
mechanical search (018) and automated epistemic infrastructure (017).

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

## DFL-01: AI Result Analysis & Pattern Surfacing

- **issue_id**: X38-DFL-01
- **classification**: Thiếu sót
- **opened_at**: 2026-03-29
- **opened_in_round**: 0
- **current_status**: Open

**Motivation**:

Every significant discovery in btc-spot-dev came from a human noticing something
unexpected in data:
- VDO: human noticed taker volume vs OHLC volume divergence
- EMA(21d) regime: human observed D1 trend filter improved all metrics 16/16
- E5 vs E0: human compared exit mechanisms, bootstrap showed P=97.2%

The framework currently has no mechanism for AI to perform this kind of pattern
detection systematically. AI cannot generate code (SSE-D-11), but it CAN analyze
results and surface patterns — a fundamentally different activity from ideation.

**Proposal**: An AI analysis layer that observes validation/backtest outputs AND
raw market data, producing structured pattern reports. This layer is:
- **Results-aware** (reads all outputs — NOT subject to SSE-D-02 results-blind rule)
- **Data-aware** (reads raw market data — price, volume, microstructure)
- **Descriptive, not prescriptive** (reports patterns, does NOT make decisions)
- **Parallel observer** (runs alongside the pipeline, does NOT modify pipeline state)

**Two analysis domains**:

| Domain | What AI analyzes | Discovery type | Example |
|--------|-----------------|---------------|---------|
| **Result analysis** | Backtest outputs, strategy performance, validation metrics | "This strategy behaves unexpectedly" | Churn filter HURTS at <30 bps (X22) |
| **Data analysis** | Raw market data, microstructure, cross-asset patterns | "This data feature is unusual" | Taker volume ≠ OHLC volume divergence (VDO origin) |

Many discoveries originate from data exploration, not strategy evaluation. VDO
was found by noticing raw taker volume behavior, not by analyzing a backtest.
EMA(21d) regime was found by observing D1 price structure, not strategy output.
The analysis layer MUST cover both domains to be effective.

**Pattern categories to surface**:

| Category | What AI looks for | Example from btc-spot-dev |
|----------|-------------------|--------------------------|
| Statistical | Unexpected significance, distributional anomalies, unusual p-values | VDO filter: DOF-corrected p=0.031 (Sharpe), p=0.004 (MDD) |
| Mathematical | Correlation structures, plateau shapes, parameter sensitivity | Cross-timescale rho=0.92, plateau spread=0.017 |
| Economic | Cost sensitivity breakpoints, regime-conditional performance | Churn filter HURTS at <30 bps (X22 finding) |
| Structural | Strategies that behave similarly despite different construction | E5 vs E0: same alpha source, different exit mechanism |
| Anomaly | Results that contradict expectations or prior knowledge | Short-side BTC: negative-EV at ALL timescales (X11) |

**Key constraint**: Analysis layer outputs are **process observations** (Type 1
evidence per Topic 007 F-22), not answer priors. They describe what IS, not what
SHOULD BE. The human decides what to investigate further.

**Open questions**:
- Trigger: Does AI analysis run automatically after every validation run, or
  on-demand by human request?
- Scope: Does it analyze individual strategy results, cross-strategy comparisons,
  or both?
- Compute: How much analysis compute is acceptable relative to backtest compute?
- History: Does the analysis layer have memory of previous reports? If so, what
  contamination rules apply to that memory?

---

## DFL-02: Human-Facing Report Contract

- **issue_id**: X38-DFL-02
- **classification**: Thiếu sót
- **opened_at**: 2026-03-29
- **opened_in_round**: 0
- **current_status**: Open

**Motivation**:

Even if DFL-01's analysis layer exists, its value depends entirely on how findings
are presented to humans. Too much noise = humans ignore reports. Too little
context = humans can't act on them.

**Proposal**: A structured report contract that defines what the analysis layer
produces and how it's organized for human consumption.

**Report structure** (per analysis run):

```
DiscoveryReport:
  run_id: str                      # Unique report identifier
  timestamp: datetime
  scope: AnalysisScope             # What was analyzed
  findings: list[Finding]          # Ordered by estimated importance

Finding:
  finding_id: str                  # DFL-YYYYMMDD-NNN
  category: PatternCategory        # statistical | mathematical | economic | structural | anomaly
  confidence: ConfidenceLevel      # high | medium | low (based on statistical power)
  summary: str                     # 1-2 sentence human-readable summary
  evidence: Evidence               # Metrics, plots, comparisons
  suggested_investigation: str     # What a human might want to look at next
  contamination_class: str         # process_observation (always, per DFL-04)
```

**Signal-to-noise management**:
- Findings ranked by estimated importance (statistical significance x economic impact)
- Low-confidence findings separated from high-confidence
- Repeat findings (same pattern seen before) flagged as "confirming" not "new"
- Maximum N findings per report to prevent overwhelm (N = debate)

**Interaction with 017 epistemic_delta.json**:
- epistemic_delta.json (017) = mandatory Stage 8 pipeline artifact, 4 fixed questions
- DiscoveryReport (019) = human-facing analysis output, open-ended pattern surfacing
- Complementary: epistemic_delta answers "what did the campaign learn?",
  DiscoveryReport answers "what's interesting that a human should see?"
- No duplication: DiscoveryReport MAY reference epistemic_delta findings but adds
  cross-run, cross-strategy, and unexpected-pattern analysis

**Open questions**:
- Maximum findings per report (N): 5? 10? 20? Based on human attention capacity
- Delivery format: markdown file? Interactive dashboard? Both?
- Acknowledgment protocol: Must human acknowledge receipt? Timeout?
- Historical access: Can humans query past reports?

---

## DFL-03: Human Feedback Capture & Grammar Evolution

- **issue_id**: X38-DFL-03
- **classification**: Judgment call
- **opened_at**: 2026-03-29
- **opened_in_round**: 0
- **current_status**: Open

**Motivation**:

The discovery loop is incomplete without a mechanism for human feedback to re-enter
the system. When a human reads a DiscoveryReport and thinks "what if we tried X?",
that insight needs a path into the framework.

SSE-D-02 says bounded ideation is results-blind. But human intuition, by
definition, is informed by experience (including seeing results). This creates a
fundamental tension: **the most valuable input to the system (human insight) is
the hardest to reconcile with the contamination model**.

**Proposal**: Three feedback channels, each with different contamination properties:

| Channel | What human provides | Contamination status | Example |
|---------|--------------------|--------------------|---------|
| **New template** | A new strategy template with declared parameters | Provenance-tracked, NOT results-blind | "Try a strategy that uses taker volume ratio as filter" |
| **Grammar extension** | New building blocks for grammar_depth1_seed | Must be results-blind (SSE-D-02) | "Add 'volume_ratio' as a grammar primitive" |
| **Investigation directive** | A question for the analysis layer to investigate | No contamination concern (meta-level) | "Compare all strategies' MDD during 2022 bear market" |

**Key design decision**: New templates from human feedback are provenance-tracked
(`source: human_insight, informed_by: DFL-report-XXX`) but NOT required to be
results-blind. This is a **deliberate exception** to SSE-D-02's results-blind rule.

**Rationale for exception**: SSE-D-02 results-blind applies to AUTOMATED ideation
(grammar enumeration, template parameterization). Human-originated templates are
fundamentally different:
- Human judgment is the ultimate authority (3-tier model)
- Human already sees results through the discovery loop — pretending otherwise is
  dishonest
- The value of human insight IS its ability to see patterns in results
- Contamination risk is managed by provenance tracking, not by blindfolding

**Grammar expansion governance**:
- New grammar primitives = expand the search space
- Must be reviewed for: does this create a combinatorial explosion?
- Grammar version tracked (grammar_hash in SSE-D-03)
- Primitives added by human are flagged `human_added` in grammar manifest

**Open questions**:
- Is the SSE-D-02 exception for human templates correct? Or does this create a
  contamination backdoor? The debate MUST address this.
- Should human feedback be anonymous (strip DFL-report-XXX reference) before
  entering grammar? This would prevent "reverse-engineering" which report
  motivated which template.
- Feedback latency: synchronous (human responds immediately) or asynchronous
  (human responds when ready, system continues)?
- Multiple humans: If multiple researchers provide feedback, how to reconcile
  conflicting directions?

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
         ↓
AI and human discuss: feasibility, design, tradeoffs
         ↓
Discussion continues — multiple rounds if needed
         ↓
Convergence: both sides agree on WHAT to build and WHY
         ↓
AI writes code (only after convergence)
         ↓
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
| Deliberation | Human ↔ AI, multiple rounds | Ensures approach is sound before coding |
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
| Process | Mechanical fill-in | Discussion → convergence → writing |
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
| Human → AI prompt | Investigation question | No contamination (meta-level) |
| Deliberation | Results, data, analysis, arguments | Results-aware (analysis, not ideation) |
| Convergence → code | Design conclusions | Provenance-tracked |
| Code → pipeline | Strategy implementation | Normal pipeline input (all gates apply) |

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

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 018 | SSE-D-02 | Bounded ideation results-blind vs discovery loop results-aware | DFL-04 defines contamination boundary; DFL-03 proposes deliberate exception for human templates |
| 018 | SSE-D-11 | APE v1 no code gen. DFL-05 proposes deliberation-gated code authoring as SEPARATE mechanism (human-initiated, convergence-gated), not exception to SSE-D-11 | DFL-05 defines scope boundary: automated gen (SSE-D-11) vs deliberation-gated authoring (DFL-05) |
| 017 | ESP-01 | epistemic_delta.json vs DiscoveryReport — complementary scope | DFL-02 defines complementary (not competing) reporting |
| 017 | ESP-04 | Budget governor vs human "investigate this" directives | DFL-03 feedback = input to human decisions, not budget override |
| 002 | F-04 | Firewall typed schema — analysis outputs need classification | DFL-04 classifies all analysis outputs as process observations |
| 003 | F-05 | Pipeline stages — discovery loop may add interaction points (human deliberation checkpoints, AI analysis hooks) | 003 owns pipeline; 019 defines interaction contracts |

## Summary table

| Issue ID | Finding | Classification | Status |
|----------|---------|---------------|--------|
| X38-DFL-01 | AI result analysis & pattern surfacing | Thiếu sót | Open |
| X38-DFL-02 | Human-facing report contract | Thiếu sót | Open |
| X38-DFL-03 | Human feedback capture & grammar evolution | Judgment call | Open |
| X38-DFL-04 | Contamination boundary for the discovery loop | Thiếu sót | Open |
| X38-DFL-05 | Deliberation-gated code authoring | Judgment call | Open |
