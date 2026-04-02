# Findings Under Review — AI Analysis & Reporting

**Topic ID**: X38-T-19B
**Opened**: 2026-04-02
**Author**: human researcher

3 findings about the core AI observation-reporting-feedback loop — how the
analysis layer observes results and data, how findings are reported to humans,
and how human feedback re-enters the system.

Split from Topic 019 (2026-04-02). DFL-01, DFL-02, DFL-03 extracted verbatim.

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
| **Data analysis** | Raw market data, microstructure | "This data feature is unusual" | Taker volume ≠ OHLC volume divergence (VDO origin) |

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

**Decision required for debate**:

| Decision | Alternatives | Implication |
|----------|-------------|-------------|
| Trigger mode | (a) Automatic post-validation (b) On-demand by human (c) Both | Automatic = more coverage but compute cost. On-demand = human bottleneck |
| Analysis scope | (a) Individual strategy (b) Cross-strategy comparison (c) Both | Cross-strategy adds value (X22 cost sensitivity finding) but increases compute |
| Memory across reports | (a) Stateless (each run independent) (b) Stateful (reference prior reports) | Stateful enables "confirming vs new" but adds contamination risk (DFL-04) |

**Open questions**:
- Compute: How much analysis compute is acceptable relative to backtest compute?
- If stateful: does the analysis layer's memory of previous reports constitute
  a contamination risk for future analyses? DFL-04 must classify.

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

**Decision required for debate**:

| Decision | Alternatives | Implication |
|----------|-------------|-------------|
| Findings cap per report | (a) Fixed N=10 (b) Dynamic by confidence (c) Uncapped | Cap prevents overwhelm; dynamic needs confidence metric definition |
| Delivery format | (a) Markdown artifact (b) Interactive (c) Markdown with standard template | Markdown is reproducible and auditable (docs/research/RESEARCH_RULES.md:57-101 [extra-archive] — Pattern A) |

**Open questions**:
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

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 017 | ESP-01 | epistemic_delta.json vs DiscoveryReport — complementary scope | DFL-02 defines complementary (not competing) reporting |
| 017 | ESP-04 | Budget governor vs human "investigate this" directives | DFL-03 feedback = input to human decisions, not budget override |
| 018 | SSE-D-02 (rule 1) | Bounded ideation results-blind vs discovery loop results-aware | DFL-03 proposes deliberate exception for human templates (D-06) |

---

## Decision summary — what debate must resolve

Debate for Topic 019B must produce decisions on these 4 questions. All are Tier 2
(mechanisms), dependent on 019A resolving D-01, D-02, D-03 first.

**Tier 2 — Mechanisms (after 019A Tier 1)**:

| ID | Decision | Finding | Alternatives |
|----|----------|---------|-------------|
| D-06 | Is the human SSE-D-02 exception for templates correct? | DFL-03 | YES (provenance-tracked) / NO (results-blind required for ALL sources) |
| D-08 | AI analysis layer: automatic or on-demand? | DFL-01 | Automatic (post-validation) / On-demand (human request) / Both |
| D-13 | AI analysis layer: stateless or stateful (memory across reports)? | DFL-01 | Stateless / Stateful (contamination risk per DFL-04) |
| D-14 | Findings cap per report? | DFL-02 | Fixed N=10 / Dynamic by confidence / Uncapped |

---

## Summary table

| Issue ID | Finding | Classification | Status |
|----------|---------|---------------|--------|
| X38-DFL-01 | AI result analysis & pattern surfacing | Thiếu sót | Open |
| X38-DFL-02 | Human-facing report contract | Thiếu sót | Open |
| X38-DFL-03 | Human feedback capture & grammar evolution | Judgment call | Open |
