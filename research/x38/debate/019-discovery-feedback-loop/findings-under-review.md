# Findings Under Review — Discovery Feedback Loop

**Topic ID**: X38-T-19
**Opened**: 2026-03-29
**Author**: human researcher

18 findings about the Human-AI collaborative discovery loop — the mechanism by
which the framework enables creative discovery of new algorithms, as distinct from
mechanical search (018) and automated epistemic infrastructure (017).

DFL-01→12: Discovery loop architecture (original, 2026-03-29/30/31).
DFL-13→18: Data foundation & quality assurance (added 2026-03-31, pre-rebuild gap fill).

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
| Delivery format | (a) Markdown artifact (b) Interactive (c) Markdown with standard template | Markdown is reproducible and auditable (RESEARCH_RULES.md Pattern A) |

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

## DFL-06: Systematic Raw Data Exploration (Untapped Fields & Patterns)

- **issue_id**: X38-DFL-06
- **classification**: Thiếu sót
- **opened_at**: 2026-03-30
- **opened_in_round**: 0
- **current_status**: Open

> **Debate scope note**: DFL-06 contains both ARCHITECTURE content (the framework
> should support systematic raw data exploration) and RESEARCH PLAN content (10
> specific analyses to run on btc-spot-dev data). The architecture decision for
> debate is D-12: should the 10 analyses be part of the framework spec (defining
> the METHOD SPACE) or deferred to the first campaign's methodology? The specific
> analyses are evidence for the architecture proposal, not binding implementation.

**Motivation**:

DFL-01 proposes an AI analysis layer. Topic 006 enumerates features from 6 known
families. But neither addresses a fundamental gap: **systematic exploration of raw
data for unknown patterns**. Topic 006 enumerates features humans already designed.
DFL-01 analyzes results humans already produced. No mechanism explores raw data
fields that have never been examined.

Data has 13 fields. Strategies use 5. Three numeric fields (`quote_volume`,
`num_trades`, `taker_buy_quote_vol`) have NEVER been used in any indicator.
Six derivable features have never been computed. Multiple analytical dimensions
have never been explored despite data being available since 2017.

**Data inventory — used vs untapped**:

```
13 fields available:
  USED (5):     open, high, low, close, taker_buy_base_vol
  UNTAPPED (4): quote_volume, num_trades, taker_buy_quote_vol, volume*

  * volume used only as VDO denominator, never analyzed independently

6 derivable features never computed:
  avg_trade_size    = quote_volume / num_trades       (institutional vs retail proxy)
  taker_buy_premium = taker_buy_quote_vol/quote_vol   (price-weighted buy pressure)
                      vs taker_buy_base_vol/volume     (volume-weighted buy pressure)
  volume_per_trade  = volume / num_trades              (participation concentration)
  quote_per_base    = quote_volume / volume            (≈ VWAP, intrabar price level)
  trade_intensity   = num_trades / (high - low)        (trades per unit price move)

3 timeframes available but underexploited:
  15m: 299,755 rows (never used in any strategy or analysis beyond X25 raw EDA)
  H1:  74,953 rows  (never used — strategies run H4 only)
  H4+D1: 96,423 rows (primary, but only D1 used for regime filter)
```

**Proposal**: 10 systematic analyses, all executable with existing data.

### Analysis 1: Microstructure Beyond VDO

**What**: Explore `quote_volume`, `num_trades`, `taker_buy_quote_vol` and derived
features for predictive content and structural patterns.

**Specific tests**:
- Forward-predictive content: each of 6 derived features vs fwd returns at
  t+1, t+6, t+24 (same methodology as X25 TBR analysis)
- Regime conditioning: do derived features behave differently in bull/bear/flat?
- VDO replacement candidates: does `taker_buy_premium` outperform simple
  `taker_buy_ratio` as entry filter?
- `trade_intensity` as volatility proxy: correlation with realized vol, ATR
- `avg_trade_size` regime shifts: do structural breaks in trade size precede
  price regime changes?
- Non-linear feature interactions: after testing individual features, test
  top-N pairwise combinations (e.g., high volume + low trade count = few
  large trades → what happens next?)

**Data required**: Existing 13-field CSV. No new data.

**Prior evidence**: X25 tested TBR forward-predictive content → near-zero.
But TBR is only 1 of 6+ derivable features. The other 5 are unexplored.
X34 tested Q-VDO-RH (volume ratio replacement) → rejected, but used only
`quote_volume` in isolation, not the full derived feature set.

### Analysis 2: Intrabar Patterns

**What**: Use 15m (300K rows) and H1 (75K rows) data to detect sub-H4 patterns
invisible at H4 resolution.

**Specific tests**:
- Intrabar volatility shape: does the distribution of sub-bar returns within
  an H4 bar predict the next H4 bar? (4×H1 or 16×15m per H4 bar)
- Opening vs closing sub-bar: is the first 15m bar of an H4 period more
  informative than the last?
- Intrabar volume profile: does volume concentration (e.g., 80% of H4 volume
  in first H1) predict direction?
- Sub-bar momentum: does H1-level momentum within an H4 bar carry over?
- Volatility term structure: compare 15m vol vs H1 vol vs H4 vol. When
  short-term vol > long-term vol (inverted), is it predictive?

**Data required**: Existing 15m and H1 CSVs. No new data.

**Prior evidence**: No prior analysis of sub-H4 patterns exists in the project.
X27 EDA analyzed H4 bars only. Strategies use H4 as minimum resolution.

### Analysis 3: Regime Transitions

**What**: Analyze WHEN and HOW D1 EMA(21) regime flips occur, and whether
transitions are predictable.

**Specific tests**:
- Transition frequency: how often does close cross EMA(21) on D1? Duration
  per regime (bull/bear)?
- Pre-transition signals: do any H4-level indicators (ATR, volume, VDO)
  shift measurably before D1 regime flips?
- False crossovers: what fraction of regime flips reverse within N bars?
  Is there a "confirmation" filter?
- Transition cost: what is the average P&L impact of being wrong about
  regime during the transition period?
- Predictability: can a simple model (logistic on H4 features) predict
  next-day regime with AUC > 0.55?

**Data required**: Existing H4+D1 data. No new data.

**Prior evidence**: X31-A tested D1 regime exit mid-trade → STOP (selectivity
0.21). But that studied EXIT timing, not ENTRY timing. Regime transition
predictability for entry has never been tested.

### Analysis 4: Time-of-Day / Day-of-Week Effects

**What**: Test whether H1/15m returns, volatility, or volume have systematic
patterns by hour-of-day or day-of-week.

**Specific tests**:
- Hourly return profile: mean return by hour (0-23 UTC) on H1 data
- Hourly volatility profile: |return| by hour — are some hours consistently
  more volatile?
- Day-of-week effects: mean return and volatility by day on D1 data
- Volume by hour: is there a systematic volume pattern? (exchange-driven,
  timezone-driven, or flat?)
- Signal timing: does strategy entry timing correlate with high/low-volume
  hours? Is performance hour-dependent?
- Calendar effects: monthly, quarterly, BTC halving cycle effects on returns
  and volatility. Are there systematic seasonal patterns?

**Data required**: Existing H1 data with `open_time` (timestamp). No new data.

**Prior evidence**: No prior time-of-day analysis exists. Crypto is 24/7 so
the assumption was "no market hours = no intraday pattern." This assumption
has never been tested.

### Analysis 5: Volume Microstructure

**What**: Analyze volume dynamics as a system — not just VDO, but volume
regime structure, non-stationarity, and interaction with returns.

**Specific tests**:
- Volume regime detection: structural breaks in rolling volume level (X27
  noted peak 24K BTC/bar 2022, drop to 3.5K by 2025). How many regimes?
  Change-point detection.
- Volume regime → return regime: does volume regime predict return
  characteristics (volatility, trend persistence)?
- `num_trades` vs `volume` divergence: when trade count is high but volume
  is low (many small trades) vs few large trades — does this predict anything?
- Volume mean-reversion: is volume ratio (current/rolling_mean) predictive
  of future |returns|?
- Non-stationarity correction: can VDO be improved by normalizing for
  volume regime? (VDO currently uses raw EMA ratio without level adjustment)
- Multi-scale VDO divergence: VDO at H1 vs H4 vs D1 — do different scales
  give different signals? When they diverge, is that informative?
  (Note: lead-lag aspect of multi-scale VDO covered in Analysis 8)

**Data required**: Existing data. No new data.

**Prior evidence**: X27 documented volume non-stationarity and found volume
predicts |return| only 1-6 bars (clustering). But no study tested volume
REGIME (structural level) as distinct from volume SIGNAL (bar-to-bar).

### Analysis 6: Higher-Order Statistical Patterns

**What**: Analyze time-varying distributional properties beyond mean and
variance.

**Specific tests**:
- Rolling kurtosis: does excess kurtosis (measured at 20.4 in X27) vary
  systematically? High-kurtosis periods vs low-kurtosis periods.
- Rolling skewness: is skewness time-varying? Does positive skew precede
  or follow trends?
- Tail dependence: are large up-moves and large down-moves clustered
  together (tail dependence) or independent?
- Variance ratio dynamics: Lo-MacKinlay VR was ~1.0 at H4 (X27). Is this
  constant or does it shift? VR > 1 = trending, VR < 1 = mean-reverting.
- Autocorrelation structure shifts: does the ACF of returns change over
  time? (e.g., stronger autocorrelation during trends)
- Shannon entropy of returns: rolling entropy as regime indicator.
  High entropy = random/efficient, low entropy = structured/trending.
  Does entropy regime predict strategy performance?

**Data required**: Existing H4 returns. No new data.

**Prior evidence**: X27 computed static statistics (kurtosis=20.4, Hurst=0.58,
VR≈1.0). No study checked whether these are TIME-VARYING.

### Analysis 7: Signal Saturation & Decay

**What**: Test whether the EMA crossover + VDO signal has degraded over time
as markets evolve.

**Specific tests**:
- Rolling Sharpe by year: is strategy Sharpe declining? (full-sample 1.45,
  but is it 2.0 in 2018 and 0.5 in 2025?)
- Signal alpha decay: regress strategy alpha on time. Slope significantly
  negative?
- Participation rate by year: are fewer trades occurring as market adapts?
- VDO discriminative power by year: does VDO filter's hit rate (% of
  filtered trades that were losers) change over time?
- Market efficiency test: is the variance ratio trending toward 1.0 from
  either direction? (Would imply market becoming more efficient)

**Data required**: Existing data + existing backtest results. No new data.

**Prior evidence**: No temporal decomposition of strategy performance exists.
Full-sample metrics (Sharpe, CAGR, MDD) are reported as single numbers.
WFO tests time-series robustness but reports aggregate win rate, not
per-window trend.

### Analysis 8: Lead-Lag Between Timeframes

**What**: Test whether lower-resolution timeframes predict higher-resolution
returns, or vice versa. Currently D1 is used only as binary regime filter
(close > EMA(21)). But D1 has rich features (volume, range, num_trades)
that may predict H4 behavior.

**Specific tests**:
- Cross-timeframe return correlation: H1 return at t vs H4 return at t+1.
  15m return at t vs H1 return at t+1. Granger-causality tests.
- D1 features → H4 next-day: does D1 volume, D1 range, D1 num_trades,
  D1 taker_buy_ratio predict next-day H4 return characteristics
  (volatility, direction, trend quality)?
- H1 momentum carry-over: does H1-level momentum within an H4 bar
  predict the NEXT H4 bar? (Distinct from Analysis 2 which looks
  at intrabar patterns within the same bar.)
- Multi-scale VDO lead-lag: does VDO at H1 lead VDO at H4? Does VDO
  scale divergence predict returns? (Structural divergence in Analysis 5;
  temporal lead-lag relationship here)
- Volatility cascade: does 15m volatility spike predict H1 volatility
  spike predict H4 volatility spike? What is the typical propagation
  time?

**Data required**: Existing 15m, H1, H4, D1 CSVs. No new data.

**Prior evidence**: No cross-timeframe predictive analysis exists. D1 is
used only as binary filter (close > EMA). X27 analyzed H4 only. The
multi-timeframe relationship is the most obvious untested dimension
given that data at 4 resolutions already exists.

**Differs from Analysis 2**: Analysis 2 looks at sub-bar structure WITHIN
one H4 bar (intrabar patterns). Analysis 8 looks at predictive
relationships ACROSS timeframes (lead-lag dynamics).

### Analysis 9: Conditional / Event-Based Dynamics

**What**: Analyze what happens AFTER specific market events. DFL-06
Analyses 1-8 examine features unconditionally (full-sample averages).
This analysis examines conditional distributions: given event X just
happened, what is the distribution of returns/volatility/volume in the
next N bars?

**Specific events to study**:
- Post-shock recovery: after a >3σ H4 return, what is the typical
  recovery pattern? Mean reversion? Continuation? Duration? Asymmetry
  (up-shocks vs down-shocks)?
- Post-VDO-cross: after VDO crosses zero (positive → negative or vice
  versa), what is the return distribution for 1/6/24 bars? Is this
  already priced into the strategy's entry signal?
- Post-regime-flip: after D1 EMA(21) regime changes, what is the
  typical trajectory? How many bars of uncertainty? What is the false
  flip rate and at what point is a flip "confirmed"?
- Post-volume-spike: after volume exceeds 3x rolling mean, what
  happens? Is the spike informative (trend start) or noise (single
  event liquidation)?
- Post-drawdown: after strategy MDD exceeds X%, what is the recovery
  distribution? Is recovery speed predictable from any features?
- Post-flat: after N consecutive bars with |return| < median, does
  a breakout follow? Probability and timing.

**Data required**: Existing H4+D1 data + existing backtest results for
strategy-conditional events. No new data.

**Prior evidence**: X31-A studied D1 regime exit mid-trade (transition
timing for exits). X27 noted pre-trend behavior (+9.16% cumulative in
20 bars before trend start). But systematic post-event dynamics across
multiple event types have never been studied.

**Differs from Analysis 3**: Analysis 3 focuses specifically on regime
transition predictability. Analysis 9 covers ALL event types (shocks,
VDO crosses, volume spikes, drawdowns, flat periods) and their
post-event dynamics.

### Analysis 10: Liquidity Proxy (Amihud Illiquidity)

**What**: Compute and analyze the Amihud illiquidity ratio — a
well-established measure of price impact per unit volume:

```
amihud = |return| / volume
```

High Amihud = illiquid (large price impact per unit traded).
Low Amihud = liquid (small price impact per unit traded).

**Specific tests**:
- Amihud time series: compute rolling Amihud on H4 data. Structural
  breaks? Trend? Regime-dependent?
- Amihud vs strategy performance: does strategy perform differently in
  high-liquidity vs low-liquidity periods? Split by Amihud tercile.
- Amihud as cost proxy: real trading cost is not constant 50 bps.
  Does Amihud predict realized slippage? If so, can it condition
  position sizing (smaller positions when illiquid)?
- Amihud and MDD: does high Amihud precede or coincide with drawdown
  periods? If predictive, it could serve as a risk management signal.
- Amihud vs VDO: is Amihud correlated with VDO? Or do they capture
  orthogonal dimensions? (VDO = directional flow pressure, Amihud =
  market depth / impact cost)

**Data required**: Existing OHLCV data (close, volume). No new data.

**Prior evidence**: No liquidity analysis exists in the project. X22
(Cost Sensitivity) analyzed strategy performance at different ASSUMED
cost levels (2-100 bps), but never measured actual market liquidity
conditions. Amihud would connect X22's cost analysis to real market
state.

**Differs from Analysis 5 (Volume Microstructure)**: Analysis 5 looks
at volume LEVEL (structural breaks, non-stationarity, regime). Analysis
10 looks at price IMPACT per unit volume — a fundamentally different
dimension. Volume can be high but liquidity low (many small trades
moving price) or volume low but liquidity adequate (few trades, tight
spread, minimal impact).

**→ Extended by DFL-15**: Roll's realized spread estimator proposed as
complementary liquidity measure, but requires tick data (inapplicable at H4).

---

**Open questions**:
- Execution order: should analyses run sequentially (each informing the next)
  or in parallel? Analysis 1 (microstructure) and Analysis 7 (saturation)
  are independent. Analysis 3 (regime transitions) may inform Analysis 4
  (time-of-day). Analysis 8 (lead-lag) is independent. Analysis 9
  (event-based) benefits from Analysis 3 results. Analysis 10 (Amihud)
  is independent.
- Minimum threshold: what constitutes an "interesting" finding from these
  analyses? p < 0.05? Economic significance > X bps?
- Integration with DFL-01: are these 10 analyses a ONE-TIME study or a
  recurring component of the DFL-01 analysis layer?
- Feature promotion path: if Analysis 1 discovers `trade_intensity` is
  predictive, what is the path to: (a) add it to Topic 006 feature
  registry, (b) create a strategy template using it, (c) validate?
  This path MUST respect DFL-03 and DFL-04 contamination rules.
  **→ Addressed by DFL-08** (Feature Candidate Graduation Path, 5 stages).
- SSE-D-02 scope: DFL-06 analyses use non-OHLCV fields (num_trades,
  quote_volume, taker_buy_quote_vol). Does SSE-D-02 hard rule 3 block this?
  **→ Addressed by DFL-09** (scope clarification: analysis ≠ ideation).

---

## DFL-07: Raw Data Analysis Methodology & Techniques

- **issue_id**: X38-DFL-07
- **classification**: Thiếu sót
- **opened_at**: 2026-03-30
- **opened_in_round**: 0
- **current_status**: Open

> **Debate scope note** (2026-03-31, gap audit): DFL-07 contains extensive
> methodology catalogs (6 categories, dozens of techniques) that are reference
> material, not architectural decisions. The actual design question is narrow:
> should the framework SPEC define a mandatory analysis methodology, or defer
> method selection to each campaign's protocol? The catalogs are evidence for
> the proposal, not binding spec content. Debate should focus on the architecture
> question, not on evaluating individual statistical methods.

**Motivation**:

DFL-06 defines WHAT to analyze (10 analyses). This finding defines HOW — the
statistical methods, visualization techniques, and discovery workflow that make
raw data analysis systematic and reproducible rather than ad-hoc.

**Relationship to DFL-01**: DFL-01 proposes an ongoing AI analysis layer.
DFL-07 provides the methodological toolkit that layer would use. If DFL-06's
analyses become recurring (per DFL-06 open question), DFL-07 is the
implementation specification for DFL-01's "data analysis" domain.
If one-time, DFL-07 is a standalone research methodology.

**Relationship to RESEARCH_RULES.md**: btc-spot-dev already has
`docs/research/RESEARCH_RULES.md` defining Pattern A (standalone runner)
and Pattern B (CLI integration) for research studies. DFL-07's workflow
EXTENDS these patterns, not replaces them:
- Phase 1-2 (SCAN, DEEP DIVE): follow Pattern A (standalone scripts)
- Phase 3 (VALIDATION): follow Pattern B (integration with validation/)
- C2 reproducibility requirements: inherit from RESEARCH_RULES.md

**Architecture vs Research Plan boundary**: DFL-07 contains both:
- **Architecture requirements** (what the framework must support):
  sections A-F define the METHOD SPACE the framework must accommodate
- **Research plan** (what to run first):
  specific technique selections, tool choices, hypothesis priorities
When Alpha-Lab is built, architecture requirements become framework
capabilities. Research plan becomes the first campaign's methodology.
These should be read as two layers, not one monolith.

The project's prior EDA (X25, X27) used basic tools (ACF, correlation, summary
stats). Many powerful techniques for structure discovery in financial time series
have never been applied. Without a defined methodology, DFL-06's 10 analyses
risk becoming another collection of scatter plots and p-values instead of a
genuine discovery engine.

---

### A. Statistical & Computational Methods

#### A1. Distributional Analysis

| Technique | Purpose | Applies to (DFL-06) |
|-----------|---------|---------------------|
| **KDE (Kernel Density Estimation)** | Non-parametric density estimation. Reveals multi-modality, fat tails, asymmetry that histograms miss | Analysis 1 (derived feature distributions), 6 (higher-order), 9 (post-event return distributions) |
| **QQ-plot (Quantile-Quantile)** | Compare empirical distribution vs theoretical (normal, Student-t). Identifies where tails deviate | Analysis 6 (tail dependence), 7 (saturation — are tails changing?) |
| **ECDF (Empirical CDF)** | Non-parametric CDF comparison between groups (regimes, time periods). More robust than histogram | Analysis 3 (regime transition), 4 (time-of-day), 9 (conditional) |
| **Two-sample KS test** | Formal test: are two distributions different? (e.g., returns in bull vs bear regime) | Analysis 3, 4, 9 — anywhere comparing conditional distributions |
| **Permutation test** | Distribution-free hypothesis testing. Already used in project (X0 component analysis). Apply to new features | Analysis 1 (are derived features predictive?), 8 (is lead-lag real?) |

#### A2. Time Series Structure

| Technique | Purpose | Applies to (DFL-06) |
|-----------|---------|---------------------|
| **Rolling statistics (mean, std, skew, kurtosis)** | Detect non-stationarity and regime shifts in any metric over time | Analysis 5 (volume), 6 (higher-order), 7 (saturation), 10 (Amihud) |
| **Structural break detection (CUSUM, Bai-Perron)** | Identify change-points in time series level or variance. More rigorous than visual inspection | Analysis 5 (volume regimes), 7 (signal decay breakpoint), 10 (liquidity regime changes) |
| **Granger causality** | Test whether lagged values of X predict Y beyond Y's own lags | Analysis 8 (lead-lag between timeframes), 1 (do derived features Granger-cause returns?) |
| **Cross-correlation function (CCF)** | Measure lead-lag correlation at multiple lags between two series | Analysis 8 (timeframe lead-lag), 5 (volume-return lead-lag) |
| **Variance ratio test (Lo-MacKinlay)** | Test random walk hypothesis at multiple horizons. Already computed once (X27) — now as rolling window | Analysis 6 (variance ratio dynamics), 7 (market efficiency over time) |
| **Autocorrelation function (ACF/PACF)** with rolling window | X27 computed static ACF. Rolling ACF reveals when serial dependence appears/disappears | Analysis 6 (autocorrelation structure shifts) |

#### A3. Dependence & Interaction

| Technique | Purpose | Applies to (DFL-06) |
|-----------|---------|---------------------|
| **Rank correlation (Spearman, Kendall)** | Non-linear dependence between features. More robust than Pearson for non-normal data | Analysis 1 (derived feature vs returns), 10 (Amihud vs VDO) |
| **Mutual information (MI)** | Captures non-linear dependence that correlation misses. MI > 0 = any dependence | Analysis 1 (feature screening — which derived features carry information about returns?) |
| **Conditional mutual information** | MI between X and Y given Z. Detects redundancy between features | Analysis 1 (pairwise interactions — does feature A add info beyond feature B?) |
| **Copula analysis** | Model dependence structure in tails separately from marginals. Captures tail dependence | Analysis 6 (tail dependence — are extreme up/down moves jointly dependent?) |
| **Information coefficient (IC)** | Rank correlation between feature and forward returns. Standard quant metric. Already used in X21 | Analysis 1 (all derived features), 8 (cross-timeframe predictors) |

#### A4. Classification & Prediction

| Technique | Purpose | Applies to (DFL-06) |
|-----------|---------|---------------------|
| **Logistic regression** | Binary classification (up/down, regime A/B). Interpretable. Already used in X14 (churn filter) | Analysis 3 (predict regime flip), 9 (predict post-event direction) |
| **Random forest feature importance** | Rank features by predictive contribution. Non-linear, handles interactions | Analysis 1 (which derived features matter most?), 8 (which timeframe features?) |
| **AUC-ROC** | Measure discriminative power of a classifier or score. Already used in X13 (AUC=0.805) | Analysis 3 (regime prediction), 4 (time-of-day predictiveness) |
| **Quantile regression** | Model conditional quantiles (not just conditional mean). Reveals asymmetric effects | Analysis 9 (post-event: median vs tail outcomes), 10 (Amihud effect on drawdown quantiles) |
| **Walk-forward validation** | Already standard in project (WFO). Apply to all predictive claims from DFL-06 | ALL analyses that claim predictive content |

#### A5. Change Detection & Segmentation

| Technique | Purpose | Applies to (DFL-06) |
|-----------|---------|---------------------|
| **Hidden Markov Model (HMM)** | Unsupervised regime detection. Discovers latent states from observed data | Analysis 3 (how many regimes exist beyond bull/bear?), 5 (volume regime count) |
| **PELT (Pruned Exact Linear Time)** | Fast change-point detection in mean/variance. Finds optimal segmentation | Analysis 5 (volume structural breaks), 7 (signal decay change-point) |
| **Ruptures library** | Multiple change-point detection algorithms (PELT, Binseg, BottomUp, Window) | Analysis 5, 7, 10 — anywhere seeking structural breaks |
| **Rolling window Fisher exact test** | Detect when a proportion (e.g., VDO hit rate) shifts significantly | Analysis 7 (VDO discriminative power decay by year) |

---

### B. Visualization Techniques

#### B1. Single-Variable Exploration

| Technique | What it reveals | When to use |
|-----------|----------------|-------------|
| **Time series + rolling mean/bands** | Trend, level shifts, volatility clustering | First look at any feature. Rolling mean ± 2σ bands |
| **Histogram + KDE overlay** | Distribution shape, multi-modality, tails | Compare feature distributions across regimes/periods |
| **Box plot by group** | Central tendency + spread + outliers across categories | Time-of-day (24 boxes), day-of-week (7), regime (2-3), year (8) |
| **Violin plot** | Full distribution shape per group (KDE + box plot) | Where box plot hides distribution shape (multi-modal groups) |
| **Cumulative sum (CUSUM) chart** | Detect persistent shifts in mean | Signal decay (Analysis 7), regime transition detection (Analysis 3) |

#### B2. Two-Variable Relationships

| Technique | What it reveals | When to use |
|-----------|----------------|-------------|
| **Scatter + regression line + confidence band** | Linear relationship, strength, outliers | Feature vs forward returns (Analysis 1, 8) |
| **Hexbin / 2D KDE** | Dense scatter where points overlap. Shows joint density | Feature vs returns when N > 10K (H4: 20K+ points) |
| **Lagged scatter matrix** | Relationships at multiple lags simultaneously | Lead-lag analysis (Analysis 8): X(t) vs Y(t+1), Y(t+2), ... |
| **Cross-correlogram** | CCF plot with confidence bands. Shows significant lead/lag | Analysis 8 (timeframe lead-lag), 5 (volume-return lag) |
| **Conditional distribution overlay** | KDE of Y given X in different quantiles | Analysis 9: return distribution given event type |

#### B3. Multi-Variable & Structure

| Technique | What it reveals | When to use |
|-----------|----------------|-------------|
| **Correlation heatmap (Spearman)** | Pairwise rank-correlation among all features | Analysis 1: screen 6+ derived features for redundancy |
| **Clustermap (hierarchical clustering)** | Group correlated features. Reveals structure in feature space | Analysis 1: which derived features form clusters? |
| **PCA biplot** | Dominant variance directions in multi-feature space | Analysis 1: do 6 derived features reduce to 2-3 principal components? |
| **Pair plot (scatter matrix)** | All pairwise scatter plots + marginal distributions | Analysis 1: initial screening of 6 derived features |
| **Calendar heatmap** | Value by (week × day-of-week) or (hour × day-of-week) | Analysis 4: time-of-day × day-of-week return/volatility patterns |

#### B4. Temporal & Regime Visualization

| Technique | What it reveals | When to use |
|-----------|----------------|-------------|
| **Regime coloring on price chart** | Overlay detected regimes on actual price | Analysis 3: visualize regime transitions on price |
| **Event study plot (mean ± CI)** | Average path around an event with confidence bands | Analysis 9: post-shock, post-VDO-cross, post-regime-flip trajectories |
| **Rolling metric chart** | Time series of rolling Sharpe, IC, AUC, entropy, etc. | Analysis 6, 7: detect when statistical properties shift |
| **Stacked area chart** | Composition over time (e.g., volume by source) | Analysis 5: taker vs maker volume composition over years |
| **Drawdown chart with liquidity overlay** | Strategy drawdown + Amihud illiquidity on same axis | Analysis 10: visual check of liquidity-drawdown relationship |

---

### C. Discovery Workflow

#### C1. Six-Category Discovery Workflow

```
Phase 1: SCAN (broad, automated)
  ├── [A] Statistical screening: IC, MI, Granger vs forward returns
  ├── [B] Visualization: correlation heatmap, pair plot, rolling stats
  ├── [D] Decomposition: FFT spectrum, wavelet scalogram, EMD/STL on
  │       key series (returns, volume, taker_buy_ratio)
  ├── [F] Domain hypotheses: run quick tests for 12 hypotheses (F1-F4)
  ├── Output: ranked feature/pattern list + anomaly flags + hypothesis
  │          confirmation/rejection table
  └── Decision: which features/patterns pass initial screening?

Phase 2: DEEP DIVE (targeted, per promising feature/pattern)
  ├── [A] Full distributional analysis (KDE, QQ, conditional)
  ├── [A5] Structural break detection (PELT, CUSUM, HMM)
  ├── [B4] Event-study and regime visualization
  ├── [D] Decomposition of target feature: wavelet denoising, EMD
  │       component isolation, frequency-domain analysis
  ├── [E] Null model test: surrogate data or GARCH simulation
  │       → pattern survives realistic baseline?
  ├── [F] If domain-driven: deeper theory test, literature comparison
  └── Decision: is the pattern robust AND distinct from known properties?

Phase 3: VALIDATION (rigorous, before any feature enters pipeline)
  ├── Walk-forward test (out-of-sample predictive power)
  ├── [E] Surrogate validation: p_surrogate < 0.05 against realistic null
  ├── Multiple testing correction (Bonferroni/Holm across all Phase 1 tests)
  ├── Economic significance (> X bps after costs?)
  ├── Redundancy check: is this independent of existing features (VDO, EMA)?
  └── Decision: proceed to DFL-03 feedback channel or discard?
```

#### C2. Reproducibility Requirements

- Every analysis produces a **dated artifact** in `research/xNN/` following
  existing RESEARCH_RULES.md patterns
- Code: standalone Python script (Pattern A or B from RESEARCH_RULES.md)
- Output: markdown report + saved figures (PNG/SVG)
- All random seeds fixed, all parameters documented
- Results must be reproducible with `python research/xNN/script.py`

#### C3. Tool Stack

| Tool | Purpose | Already in project? |
|------|---------|-------------------|
| `numpy`, `pandas` | Data manipulation, rolling stats | Yes |
| `scipy.stats` | Statistical tests (KS, Granger proxy, permutation) | Yes |
| `scipy.signal` | FFT, Welch spectral density, coherence | Yes |
| `statsmodels` | ACF/PACF, variance ratio, Granger causality, quantile regression, STL | Yes |
| `matplotlib`, `seaborn` | Visualization (all B1-B4 techniques) | Yes |
| `scikit-learn` | Random forest, PCA, mutual information, AUC-ROC | Yes |
| `ruptures` | Change-point detection (PELT, Binseg) | **No — needs install** |
| `hmmlearn` | Hidden Markov Models for regime detection | **No — needs install** |
| `arch` | GARCH/GJR-GARCH simulation, variance ratio tests | Check availability |
| `PyWavelets` | Wavelet decomposition (DWT, CWT, scalogram) | **No — needs install** |
| `EMD-signal` | Empirical Mode Decomposition, VMD | **No — needs install** |

#### C4. Contamination Safeguard

Per DFL-04 constraints:
- Phase 1-2 outputs = **process observations** (Type 1 evidence). They
  describe data, not prescribe strategy decisions.
- Phase 3 WFO validation = same methodology as existing project validation.
  No special exemptions.
- If a feature passes Phase 3 and enters DFL-03 feedback:
  - As **new template**: provenance-tracked, NOT results-blind (DFL-03 rule)
  - As **grammar extension**: MUST be results-blind — the primitive must be
    defensible from data structure alone, not from backtested performance
  - As **investigation directive**: no contamination concern

---

### D. Signal Decomposition — Transform Data BEFORE Analysis

Statistical methods (A) analyze data as-is. Decomposition TRANSFORMS data
into components first, creating new representations that reveal hidden
structure (cycles, multi-scale trends, noise) invisible in raw time series.

#### D1. Frequency Domain

| Technique | What it reveals | Applies to (DFL-06) |
|-----------|----------------|---------------------|
| **FFT (Fast Fourier Transform)** | Dominant frequencies / hidden cycles. Power spectrum shows which periodicities carry energy | Analysis 4 (time-of-day: is there a 24h cycle? 168h weekly cycle? 4h cycle in volume?) |
| **Spectral density estimation (Welch)** | Smoothed power spectrum — more robust than raw FFT. Confidence bands on peaks | Analysis 4 (verify cycles are statistically significant, not noise) |
| **Coherence spectrum** | Frequency-domain correlation between two series. At which frequencies are they related? | Analysis 8 (lead-lag: are H1 and H4 returns coherent at specific frequencies?) |

**Limitation**: FFT assumes stationarity over the full window. Financial
data is non-stationary. Use SHORT windows or prefer wavelets (D2).

#### D2. Time-Frequency Domain

| Technique | What it reveals | Applies to (DFL-06) |
|-----------|----------------|---------------------|
| **DWT (Discrete Wavelet Transform)** | Multi-scale decomposition preserving time locality. Separate trend (low-freq) from noise (high-freq) at each time point | Analysis 2 (intrabar: decompose H4 bar into trend + noise using 15m sub-bars), Analysis 6 (rolling higher-order stats on wavelet-denoised series) |
| **CWT (Continuous Wavelet Transform)** | Scalogram — 2D map of power by (time × frequency). Shows WHEN cycles appear/disappear | Analysis 7 (saturation: does the dominant cycle change over time? Signal frequency shifting?) |
| **Wavelet coherence** | Time-varying coherence between two series at multiple scales | Analysis 8 (lead-lag: does H1→H4 lead-lag exist only at certain scales? Only during certain periods?) |

**Key value**: Wavelets reveal that a pattern exists at scale X during
period Y but not period Z. This is invisible to both static FFT and
rolling-window statistical methods.

#### D3. Adaptive Decomposition

| Technique | What it reveals | Applies to (DFL-06) |
|-----------|----------------|---------------------|
| **EMD (Empirical Mode Decomposition)** | Data-driven: decomposes into Intrinsic Mode Functions (IMFs) without pre-chosen basis. Each IMF = one oscillatory component | Analysis 5 (volume: separate structural level from seasonal from noise — each IMF analyzable separately) |
| **STL (Seasonal-Trend-Loess)** | Separates time series into Seasonal + Trend + Residual. Requires specifying period | Analysis 4 (extract 24h seasonal from H1 data, 7-day seasonal from D1), Analysis 5 (volume trend vs seasonal) |
| **Variational Mode Decomposition (VMD)** | Like EMD but more robust to noise and mode mixing. Decomposes into K modes at specified bandwidths | Analysis 3 (regime: decompose price into slow regime component + fast oscillation — regime transitions visible in slow component) |

**Key value for DFL-06**: Decompose volume into structural_level (IMF 1-2)
+ seasonal (IMF 3-4) + noise (IMF 5+). Then Analysis 5 tests structural_level
for regime breaks. Analysis 4 tests seasonal for time-of-day effects. Each
component becomes a SEPARATE input to statistical methods (A).

#### D4. Decomposition → Feature Pipeline

```
Raw H4 bar data (13 fields)
       │
       ├──→ [FFT] ──→ dominant_cycle_period, spectral_peak_power
       ├──→ [DWT] ──→ trend_component, noise_component, detail_coefficients
       ���──→ [EMD] ──→ IMF_1 (trend), IMF_2 (cycle), ..., residual
       └──→ [STL] ──→ seasonal_24h, trend, residual
              │
              ▼
       New derived features (input to Analysis 1-10 and methods A1-A5)
```

Each decomposition output is a NEW time series that can be analyzed with
ALL techniques in sections A and B. This multiplies the discovery surface:
10 analyses × 4 decomposition methods = 40 analysis paths (most won't
yield results, but some may reveal structure invisible in raw data).

---

### E. Null Model / Synthetic Baseline — Distinguish Real vs Artifact

Statistical significance (p-value) answers "is this pattern unlikely under
H0?" But the default H0 (iid normal) is WRONG for financial data. BTC/USDT
has fat tails, volatility clustering, and serial dependence in |returns|.
A pattern that looks "significant" against iid normal may be a trivial
consequence of these known properties.

Null models create REALISTIC synthetic baselines that preserve known
statistical properties, so only GENUINELY NEW patterns pass the test.

#### E1. Surrogate Data Methods

| Technique | What it preserves | What it destroys | Use for |
|-----------|------------------|-----------------|---------|
| **Random shuffle** | Marginal distribution (mean, variance, kurtosis) | ALL temporal structure | Baseline: "is temporal ordering necessary for this pattern?" |
| **Phase randomization (IAAFT)** | Marginal distribution + power spectrum (autocorrelation) | Non-linear dependencies, higher-order temporal structure | Baseline: "does this pattern require non-linear structure, or does linear autocorrelation explain it?" |
| **Block bootstrap** | Local temporal structure within blocks | Long-range dependencies | Baseline: "does this pattern require structure beyond N-bar windows?" Already used in VCBB (research/lib/vcbb.py) |
| **Stationary bootstrap** | Temporal structure with random block lengths | Long-range order with geometric block sampling | More robust than fixed-block bootstrap for non-stationary data |

#### E2. Parametric Null Models

| Model | What it captures | Use for |
|-------|-----------------|---------|
| **GARCH(1,1)** | Volatility clustering + fat tails (conditional heteroskedasticity) | "Does this pattern survive after accounting for vol clustering?" Fit GARCH → simulate 1000 paths → re-run analysis on each → percentile rank real result |
| **GJR-GARCH** | Asymmetric volatility (leverage effect: down-moves increase vol more than up-moves) | Same as GARCH but captures asymmetry. More realistic for BTC |
| **AR(p)-GARCH(1,1)** | Linear return predictability + volatility clustering | "Does the predictive signal survive after removing known autocorrelation + vol dynamics?" |

#### E3. Application to DFL-06 Analyses

| DFL-06 Analysis | Null model to use | What it validates |
|-----------------|------------------|-------------------|
| Analysis 1 (microstructure) | Phase randomization | "Does trade_intensity predict returns, or does any series with same ACF show this?" |
| Analysis 2 (intrabar) | Block bootstrap (H4-aligned) | "Do sub-bar patterns predict next bar, or does local structure explain it?" |
| Analysis 3 (regime transitions) | GARCH simulation | "Are transitions predictable, or does vol clustering create apparent predictability?" |
| Analysis 4 (time-of-day) | Block bootstrap (24h blocks) | "Is hourly pattern real, or artifact of vol clustering within days?" |
| Analysis 5 (volume) | Phase randomization of volume | "Do volume regime breaks predict return regime, or mechanical vol-volume coupling?" |
| Analysis 6 (higher-order) | GARCH simulation | "Is rolling kurtosis time-varying BEYOND what GARCH predicts?" |
| Analysis 7 (signal decay) | Stationary bootstrap | "Is Sharpe declining, or within normal variation of stationary process?" |
| Analysis 8 (lead-lag) | Phase randomization (bivariate) | "Does H1 lead H4, or does any pair with same cross-spectrum show this?" |
| Analysis 9 (event-based) | Conditional block bootstrap | "Is post-shock behavior special, or do GARCH large moves always look like this?" |
| Analysis 10 (Amihud) | Shuffle Amihud vs returns | "Does Amihud predict drawdowns, or mechanical relationship (both driven by vol)?" |

#### E4. Validation Protocol

```
For every pattern P discovered in DFL-06:

1. Define appropriate null model M (choose from E1/E2 based on what
   known property might explain P)
2. Generate N=1000 synthetic datasets from M
3. Compute test statistic T on each synthetic dataset
4. Compute T on real data
5. p_surrogate = fraction of synthetic T ≥ real T
6. Pattern P is REAL only if p_surrogate < 0.05

This is SEPARATE from and IN ADDITION to standard statistical tests (A).
A pattern must pass BOTH:
  - Standard test (A1-A5): significant vs iid null
  - Surrogate test (E): significant vs realistic null
```

---

### F. Domain-Driven Hypothesis Testing — Theory → Data, Not Data → Theory

Sections A-E are DATA-DRIVEN: explore data → find patterns → test them.
Section F is THEORY-DRIVEN: start from financial theory → derive testable
prediction → confirm or reject in BTC/USDT data.

Both directions are necessary. Data-driven finds the unexpected. Theory-driven
finds the expected-but-unverified. Together they cover the full discovery space.

#### F1. Market Microstructure Hypotheses

| Hypothesis | Source | Testable prediction | Data needed |
|------------|--------|--------------------|----|
| **Kyle's lambda (price impact)** | Kyle (1985) | Δprice = λ × signed_volume + ε. λ > 0, λ varies over time. High λ = illiquid. | Existing: taker_buy_base_vol as signed flow proxy, close as price. Regression per rolling window |
| **Volume-volatility mixture** | Clark (1973), Tauchen & Pitts (1983) | Volume = proxy for information arrival rate. If true: num_trades should predict realized vol better than raw volume | Existing: num_trades, volume, realized vol from H4 returns |
| **Informed trading detection** | Easley & O'Hara (VPIN, 2012) | Imbalance in taker flow = informed traders acting. Extreme imbalance → larger subsequent |return| | Existing: taker_buy_ratio as VPIN proxy. Test: extreme TBR → higher |fwd_return| |

#### F2. Behavioral Finance Hypotheses

| Hypothesis | Source | Testable prediction | Data needed |
|------------|--------|--------------------|----|
| **Momentum life cycle** | Jegadeesh & Titman (1993); Hong & Stein (1999) | Momentum profits: build (underreaction) → peak → decay (overreaction) → reversal. Testable as cross-horizon return autocorrelation profile | Existing: H4/D1 returns at multiple horizons. Compute ACF at lags 1, 6, 24, 72, 144 |
| **Herding / crowded trade** | Banerjee (1992) | When taker_buy_ratio reaches extremes (>0.55 or <0.45), market is one-sided → mean reversion likely | Existing: taker_buy_ratio. Test: conditional return distribution when TBR in top/bottom decile |
| **Disposition effect** | Shefrin & Statman (1985) | Traders sell winners too early, hold losers too long. If present in BTC: volume should spike after price recovers to recent high | Existing: volume + high_watermark derived from close |

#### F3. Market Efficiency Hypotheses

| Hypothesis | Source | Testable prediction | Data needed |
|------------|--------|--------------------|----|
| **Adaptive Market Hypothesis** | Lo (2004) | Market efficiency is time-varying. Predictability appears/disappears | Existing: rolling VR + ACF + Sharpe (Analysis 6/7). **Note**: AMH is an interpretive FRAMEWORK, not a single testable prediction. The "test" = Analysis 6/7 results interpreted through AMH lens. Reclassified as interpretive lens, not standalone hypothesis |
| **Fractal Market Hypothesis** | Peters (1994) | Instability when one horizon dominates participation | Existing: multi-timeframe volume data. **Specific testable prediction**: volume concentration at one timeframe → subsequent volatility. FMH as a whole is a framework, but this prediction IS testable |
| **Volatility feedback** | Campbell & Hentschel (1992) | Increased volatility → higher risk premium → lower prices (or higher expected returns). Asymmetric: vol up → price down stronger than vol down → price up | Existing: realized vol vs subsequent returns. Asymmetry test: separate up-vol periods vs down-vol periods |

#### F4. Crypto-Specific Hypotheses

| Hypothesis | Source | Testable prediction | Data needed |
|------------|--------|--------------------|----|
| **Halving cycle** | BTC supply schedule | Returns cluster in post-halving years (scarcity narrative). Testable: returns in months 0-18 post-halving vs other months | Existing: D1 returns + known halving dates (2016-07, 2020-05, 2024-04) |
| **Weekend effect** | Crypto-specific studies | Different return/volatility characteristics on weekends vs weekdays. Unlike TradFi (where weekend = no trading), crypto trades 24/7 but human attention varies | Existing: H1/D1 with timestamps. Analysis 4 partially covers this, but framing as crypto-specific hypothesis adds depth |
| **Funding rate proxy** | Perpetual futures market | When spot market shows strong directional taker flow, perp funding rate is likely extreme → crowded trade → reversal. Taker_buy_ratio as funding proxy | Existing: taker_buy_ratio. Test: does extreme TBR predict reversal with similar timing as known funding rate spikes? |

#### F5. Theory → DFL-06 Analysis Mapping

Each hypothesis can be tested WITHIN an existing DFL-06 analysis:

| Hypothesis | Primary DFL-06 Analysis | Additional test |
|------------|------------------------|-----------------|
| Kyle's lambda | Analysis 10 (Amihud is a simplified Kyle model) | Rolling λ estimation, λ vs strategy MDD |
| Volume-volatility mixture | Analysis 5 (volume microstructure) | num_trades vs realized_vol regression |
| Informed trading (VPIN) | Analysis 1 (microstructure) | TBR extremes → |fwd_return| conditional test |
| Momentum life cycle | Analysis 7 (saturation) | Multi-horizon ACF profile |
| Herding | Analysis 1 (microstructure) + Analysis 9 (event-based) | TBR extreme → conditional return KDE |
| Disposition effect | Analysis 9 (event-based) | Volume spike at high-watermark recovery |
| Adaptive Market | Analysis 6 (higher-order) + Analysis 7 (saturation) | Rolling VR + rolling Sharpe joint analysis |
| Fractal Market | Analysis 8 (lead-lag) | Volume concentration index across timeframes |
| Volatility feedback | Analysis 6 (higher-order) | Asymmetric vol→return regression |
| Halving cycle | Analysis 4 (calendar effects) | Post-halving month dummy variable |
| Weekend effect | Analysis 4 (time-of-day) | Weekend dummy on returns + vol |
| Funding rate proxy | Analysis 1 + Analysis 9 | Extreme TBR → reversal event study |

---

**Open questions**:
- Which Phase 1 screening metric is primary? IC (linear) vs MI (non-linear)?
  Use both and compare, or pick one as gate?
- Phase 2 depth: how many bars of analysis per feature before declaring
  "robust" or "spurious"? Risk of over-analysis (multiple testing).
- Phase 3 significance threshold: p < 0.05 after Holm correction? Or
  economic threshold (> X bps per trade) as primary gate?
- Surrogate method selection: should every DFL-06 analysis use the SAME
  null model (e.g., GARCH for all), or should each analysis use the most
  appropriate model from E1/E2? Latter is more rigorous but requires
  per-analysis judgment.
- Tool installation: `ruptures`, `hmmlearn`, `PyWavelets`, `EMD-signal`
  are not in current venv. Add to `pyproject.toml` or keep as optional
  research dependencies?
- Automation vs manual: should Phase 1 SCAN run automatically when new
  data arrives, or only on human request? (Interacts with DFL-01 trigger
  question.)
- Notebook vs script: DFL-06 analyses are exploratory by nature. Allow
  Jupyter notebooks for Phase 1-2 (exploration), require scripts for
  Phase 3 (validation)?
- Domain hypothesis priority: all 12 hypotheses in parallel, or rank by
  expected value and test sequentially? Kyle's lambda and momentum
  life cycle have strongest literature support for crypto.

---

## DFL-08: Feature Candidate Graduation Path

- **issue_id**: X38-DFL-08
- **classification**: Thiếu sót
- **opened_at**: 2026-03-31
- **opened_in_round**: 0
- **current_status**: Open

**Motivation**:

DFL-06 defines 10 systematic analyses for raw data exploration. DFL-07 defines
the methodology (statistical methods, visualization, workflow). DFL-01 defines
the AI analysis layer. DFL-02 defines the report contract. DFL-03 defines human
feedback channels. F-08 (Topic 006) defines the feature registry.

But NO finding defines the **end-to-end path** from "pattern discovered in raw
data" to "feature registered and available for strategy generation." Each finding
covers one segment:

```
DFL-01 executes DFL-06 analyses (using DFL-07 methodology)
  → [?1] → DFL-02 report → human review → [?2] → DFL-03 channel
  → [?3] → F-08 registry → strategy validation
```

The `[?]` gaps are:
1. What acceptance criteria must a raw pattern from DFL-06 analysis meet
   to become a `feature_candidate` and enter a DFL-02 report?
2. What decision framework does the human use to choose TEMPLATE vs
   GRAMMAR vs INVESTIGATE vs DISCARD? (DFL-03 defines channels but not
   decision criteria)
3. How does a human-approved feature from DFL-03 enter the F-08 registry
   with correct metadata, provenance, and generation_mode?

Without this path, DFL-06's 10 analyses produce findings that have no defined
route into the production framework. DFL-06's own open question (line "Feature
promotion path") explicitly flags this gap.

**Proposal**: A 5-stage graduation path with defined gates between stages.

### Stage 1: Discovery → Candidate

**Input**: DFL-06 analysis output (Phase 1 SCAN) OR DFL-12 grammar depth-2 output
**Gate**: Top-N by MI rank (N declared before screening, per DFL-11 Tier 0).
Not a p-value threshold — fixed N avoids passing ~14K features under H0.
**Output**: `feature_candidate` record with:
  - `candidate_id`: DFL-FC-YYYYMMDD-NNN
  - `source_analysis`: which DFL-06 analysis (1-10) produced it
  - `raw_fields_used`: which of the 13 data fields
  - `derivation`: formula or transformation applied
  - `screening_metrics`: IC, MI, p-value from Phase 1
  - `contamination_class`: process_observation (always, per DFL-04)

**Who runs**: AI analysis layer (DFL-01) during Phase 1 SCAN, or human
researcher running DFL-06 analyses manually.

### Stage 2: Candidate → Deep Dive Report

**Input**: feature_candidate from Stage 1
**Gate**: DFL-07 Phase 2 DEEP DIVE passes — pattern survives:
  - Full distributional analysis (robust across regimes/periods)
  - Structural break detection (not an artifact of one regime)
    **→ Extended by DFL-14** (shelf-life classification) **and DFL-18** (regime-conditional profiling)
  - Null model test (E1/E2 from DFL-07 §E: p_surrogate < 0.05)
**Output**: Finding entry in DFL-02 DiscoveryReport with:
  - Full evidence bundle (plots, statistics, null model results)
  - `suggested_investigation`: specific next step for human
  - Redundancy assessment: correlation with existing features (VDO, EMA, ATR)

### Stage 3: Report → Human Decision

**Input**: DFL-02 DiscoveryReport finding
**Gate**: Human reviews report and decides one of:
  - **INVESTIGATE**: request deeper analysis (loops back to Stage 2, internal to
    graduation path — does not use a DFL-03 channel)
  - **TEMPLATE**: create new strategy template using the feature (DFL-03 channel 1)
  - **GRAMMAR**: propose grammar primitive for the feature (DFL-03 channel 2)
  - **DISCARD**: insufficient evidence or economic significance (internal decision,
    no DFL-03 channel)
**Output**: Human decision record with provenance (which report finding).
Only TEMPLATE and GRAMMAR exit the graduation path into DFL-03 channels.

**Who decides**: Human researcher (Tier 3 authority per 3-tier model).
AI analysis layer CANNOT promote features — only surface them.

### Stage 4: Human Decision → Feature Registry

**Input**: Human TEMPLATE or GRAMMAR decision from Stage 3
**Gate**: Feature must satisfy F-08 (Topic 006) registry acceptance criteria:
  - Belongs to a declared feature family (or creates new family with justification)
  - Has defined lookback(s), tail(s), threshold calibration mode
  - Passes registry_acceptance test for auto-generated features (if via grammar)
  - DFL-04 contamination class recorded in registry metadata
**Output**: Feature registered in F-08 registry with:
  - `source: discovery_loop`
  - `provenance: DFL-FC-YYYYMMDD-NNN → DFL-report-XXX → human_decision_YYY`
  - `generation_mode`: `human_template` or `grammar_extension` (extends SSE-D-03
    vocabulary — SSE-D-03 defines `grammar_depth1_seed` and `registry_only` for
    automated generation; discovery loop adds these two values for human-originated
    features. Topic 006 registry must accept the extended vocabulary.)

**Contamination rules**:
  - TEMPLATE path: provenance-tracked, NOT results-blind (DFL-03 exception)
  - GRAMMAR path: primitive MUST be results-blind (SSE-D-02 hard rule)
  - Both paths: feature enters normal validation — no shortcuts

### Stage 5: Registry → Strategy Validation

**Input**: Registered feature from Stage 4
**Gate**: Normal validation pipeline (all 7 gates from CLAUDE.md)
**Output**: Strategy using the feature receives PROMOTE/HOLD/REJECT verdict

This stage is NOT new — it is the existing validation pipeline. Included here
to make the end-to-end path explicit and to confirm: discovery loop features
receive NO special treatment in validation.

### Governance properties

| Property | Value |
|----------|-------|
| Human veto | Any stage (Tier 3 authority) |
| AI authority | Stage 1 (screening) and Stage 2 (deep dive) only |
| Contamination | Tracked end-to-end via provenance chain |
| Reversibility | Feature can be de-registered if validation fails |
| Multiple testing | Stage 5 Holm-corrected across all formally validated features (§9) |
| Cycle time | Not specified — depends on analysis complexity |

### Interaction with existing findings

| Finding | Role in graduation path |
|---------|----------------------|
| DFL-06 | Source: produces raw patterns (Stage 1 input) |
| DFL-07 | Methodology: defines Phase 1/2/3 workflow (Stage 1-2 methods) |
| DFL-01 | Executor: AI analysis layer runs Stage 1-2 |
| DFL-02 | Format: Stage 2 output follows report contract |
| DFL-03 | Channel: Stage 3 human decision uses feedback channels |
| DFL-04 | Constraint: contamination rules at every stage |
| DFL-05 | Code: if feature needs novel code, deliberation-gated authoring applies |
| F-08 (006) | Destination: Stage 4 registry acceptance |
| SSE-D-02 (018) | Constraint: grammar extensions must be results-blind |
| SSE-D-03 (018) | Vocabulary: generation_mode extended with `human_template`, `grammar_extension` |

**Open questions**:
- Stage 1 gate design: top-N by MI rank (per DFL-11 Tier 0) with N declared
  before screening. What is the right N? (200? 100? 500?) Should N be
  calibrated from existing features or fixed a priori?
- Stage 2 redundancy: if a new feature correlates r > 0.8 with VDO, is it
  automatically discarded? Or can it replace VDO if strictly superior?
- Stage 3 latency: how long can a report finding sit without human decision
  before it expires? (Prevents stale findings accumulating)
- Batch vs streaming: do features graduate one at a time, or can Stage 1
  produce a batch that moves through stages together?
- Feedback loop: if a Stage 5 validation REJECTS a feature, does that
  information feed back to Stage 1 screening thresholds? (Risk: overfitting
  the graduation path to past rejections. Also: rejection info flowing to
  screening = results → analysis pipeline, which DFL-04 must classify.)

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
The concern: if grammar enumeration can use 13 fields × unlimited derived
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

## DFL-10: Pipeline Integration — Data Characterization as Prerequisite Stage

- **issue_id**: X38-DFL-10
- **classification**: Thiếu sót
- **opened_at**: 2026-03-31
- **opened_in_round**: 0
- **current_status**: Open

**Motivation**:

The current 8-stage pipeline (F-05, Topic 003) has a coverage gap between Stage 2
and Stage 3:

```
Stage 2: Data audit (integrity)  →  Stage 3: Single-feature scan (grammar-defined)
```

Stage 2 checks data INTEGRITY: gaps, duplicates, checksums, anomaly disposition.
Stage 3 scans features defined by GRAMMAR: exhaustive enumeration of grammar-declared
building blocks (50K+ configurations from OHLCV primitives).

No stage characterizes the data itself — distributional properties, field coverage,
temporal structure, or pairwise dependencies (F-05 enumerates 8 stages without a
profiling step; `003-protocol-engine/findings-under-review.md` lines 29-39). Grammar
design (which determines Stage 3's search space) proceeds blind to data properties.

**Systematic coverage gap**:

| Metric | Current pipeline | With Stage 2.5 |
|--------|-----------------|----------------|
| Fields profiled before grammar design | 0/13 | 13/13 |
| Fields in grammar (btc-spot-dev) | 5/13 (OHLCV) | 5+/13 (informed expansion) |
| Numeric fields never analyzed | 3 (`quote_volume`, `num_trades`, `taker_buy_quote_vol`) | 0 |
| Data properties known before scan | Integrity only | Integrity + distributional + temporal + dependence |

**Evidence**:

1. **Coverage blind spot** (DFL-06): btc-spot-dev has 13 data fields. Grammar
   covers 5. Three numeric fields have NEVER been statistically profiled. The
   pipeline cannot discover patterns in data dimensions it does not examine.

2. **Discovery origin**: VDO — the project's most significant filter — was
   discovered by a human noticing taker volume behavior in raw data. This field
   was outside grammar scope, found by exploratory observation, not systematic
   process (Topic 019 README lines 9-11: "100% of project alpha came from
   human intuition"). A data characterization stage would have surfaced this
   field's properties systematically before grammar design.

3. **V6/V7 precedent** (P-01, `docs/v6_v7_spec_patterns.md` line 58): Anomaly
   Disposition Register pattern requires an artifact after Stage 2 and before
   Stage 3. x38 inherits the pattern name but not the practice of comprehensive
   data profiling.

4. **Consistent with Topic 018**: SSE-D-02 (CLOSED, authoritative) mandates
   machine-verifiable evidence first — ideation rules are results-blind,
   compile-only, OHLCV-only, provenance-tracked. The extra-canonical 4-agent
   debate additionally rejected "human causal story" as a gate
   (`docs/search-space-expansion/debate/claude/claude_debate_lan_2.md:219`:
   "machine-verifiable phải chốt trước; causal story là explanatory layer sau
   evidence"; note: extra-canonical = input evidence, not standard-debate
   decision). Data characterization is NOT a causal story — every output is
   machine-computable descriptive statistics. No "why does this pattern exist?"
   is required.

**Proposal**: Insert **Stage 2.5 "Data Characterization"** between Stage 2
(Data audit) and Stage 3 (Single-feature scan).

### Stage 2.5 specification

| Property | Value |
|----------|-------|
| **Name** | Data Characterization |
| **Position** | After Stage 2 (Data audit), before Stage 3 (Feature scan) |
| **Input** | `audit_report.json` (Stage 2), raw data files |
| **Output** | `data_profile.json` |
| **Gate** | Stage 3 BLOCKED until `data_profile.json` exists |
| **Compute ceiling** | < 30 minutes (profiling, not investigation) |
| **Scope** | Descriptive statistics only — no causal interpretation, no strategy decisions |

**Scope note**: The specification above is a PROPOSAL from Topic 019, illustrating
what data characterization could look like. Topic 003 owns pipeline stage design
and may modify, simplify, or reject any element. The core claim from 019 is that
a data profiling step is NEEDED before grammar design — the specific implementation
is 003's decision.

### `data_profile.json` contents

| Section | Contents | Purpose |
|---------|----------|---------|
| **field_inventory** | All fields, dtypes, basic stats (count, mean, std, min, max, nulls) | Know what data exists |
| **distributional_profile** | Per field: normality test, stationarity test, structural break count | Know data properties before grammar design |
| **pairwise_dependencies** | Rank correlation matrix + nonlinear dependence measure for all numeric field pairs | Identify informative fields and redundancies |
| **temporal_structure** | Autocorrelation summary per field (significant lags at protocol-defined α) | Know temporal properties for feature design |
| **coverage_map** | `grammar_fields` vs `all_fields`, `coverage_ratio`, fields NOT in grammar flagged | Make grammar gaps visible to protocol |

### What this is NOT

| Concern | Answer |
|---------|--------|
| "Causal story gate" (018 rejected) | No. Machine-computable descriptive statistics. No "why" required. Consistent with 018's "machine-verifiable first" |
| "Full DFL-06 suite" | No. Stage 2.5 = shallow profiling (< 30 min). DFL-06 = deep investigation (10 analyses, days). "What properties exist?" vs "what exploitable patterns exist?" |
| "Modifies SSE-D-02" | No. Grammar (Stage 3) remains OHLCV-only. Stage 2.5 profiles ALL fields for awareness. Non-OHLCV findings route to human templates (DFL-03/09) |
| "Blocks on interpretation" | No. Gate is mechanical: `data_profile.json` exists → Stage 3 unblocked. Coverage ratio is informational |
| "Replaces parallel observer" | No. DFL-06/07 = deep analysis (DFL-01 layer). Stage 2.5 = pipeline infrastructure. Complementary |

### Interaction with existing findings

| Finding | Relationship |
|---------|-------------|
| DFL-06 | Shallow (2.5) vs deep (06). Stage 2.5 output feeds DFL-06 as starting point |
| DFL-07 | Methodology for deep dives. Not needed for Stage 2.5 (standard descriptive stats) |
| DFL-08 | Graduation path after discovery. Stage 2.5 is pre-discovery infrastructure |
| DFL-09 | Scope: analysis ≠ ideation. Stage 2.5 profiles all fields (analysis). Consistent |
| DFL-01 | AI analysis layer. Stage 2.5 output enriches DFL-01 input |
| F-05 (003) | 8-stage pipeline. DFL-10 proposes Stage 2.5 → 9 stages. **003 owns this decision** |
| P-01 (V6) | Anomaly Disposition Register. Stage 2.5 extends this proven pattern |

### Design alternative: expand Stage 2 scope

Instead of inserting Stage 2.5, broaden Stage 2 "Data audit" to include
characterization:

| Option | Pros | Cons |
|--------|------|------|
| **New Stage 2.5** | Clean separation (integrity ≠ profiling). Explicit requirement. Campaign-skippable if data unchanged | 9 stages vs V6's 8. Pipeline amendment needed |
| **Expand Stage 2** | Keeps 8 stages. "Audit" naturally extends | Overloads scope. Mixes integrity with statistics. Harder to separate concerns |

Judgment call for Topic 003. DFL-10 proposes Stage 2.5 but acknowledges the
alternative.

**Open questions**:
- Stage 2.5 vs expanded Stage 2: does 8→9 break design assumptions (state
  machine hash, directory structure, V6 compatibility)?
- Coverage_ratio: informational only (logged) or advisory (protocol warning)?
  Hard gating would force grammar to cover ALL fields, which may be wrong
  for noisy fields.
- Campaign reuse: if data is identical between campaigns, can `data_profile.json`
  be reused? Reuse = efficiency. Re-run = catches data corrections.
- Method configurability: fixed test battery or protocol-configurable
  per campaign? (Specific test selection is implementation detail for 003.)
- DFL-06 integration: does DFL-06 consume Stage 2.5 output, or run
  independently? Consuming = faster start. Independent = no Stage 2.5
  dependency for analysis.

---

## DFL-11: Statistical Budget Accounting

- **issue_id**: X38-DFL-11
- **classification**: Thiếu sót
- **opened_at**: 2026-03-31
- **opened_in_round**: 0
- **current_status**: Open

**Motivation**:

DFL-06 proposes 10 systematic analyses. DFL-07 proposes statistical methods
including MI, IC, permutation tests. DFL-08 proposes a 5-stage graduation path
with gates. But NO finding addresses the **fundamental statistical constraint**
on how many features can be discovered and validated from a finite dataset.

**The binding constraint on feature invention is not search technology — it is
statistical power.**

btc-spot-dev empirical parameters:

```
N_trades ≈ 188          (E5-ema21D1, 2017-08 → 2026-02, harsh 50bps)
Timespan: 8.5 years     (single asset, single timeframe family)
M_eff ≈ 4.35            (Nyholt effective DOF across 16 timescales)
```

**Multiple testing cost scales with features tested**:

When K features are formally tested, family-wise error control requires
adjusted significance thresholds:

| Features tested (K) | Bonferroni α_adj | VDO (p=0.031) survives? | Required effect for 80% power |
|---------------------|-----------------|------------------------|-------------------------------|
| 1 (human picks VDO) | 0.050 | YES ✓ | Δ_Sharpe ≈ 0.20 |
| 10 (small grammar) | 0.005 | NO ✗ | Δ_Sharpe ≈ 0.35 |
| 100 (depth-2 grammar) | 0.0005 | NO ✗ | Δ_Sharpe ≈ 0.50 |
| 10,000 (GP search) | 0.000005 | NO ✗ | Δ_Sharpe ≈ 0.70 |

**The paradox**: Automated search finds more features, but each feature requires
stronger evidence to validate. With N=188 trades, there exists a hard ceiling
on how many features can be fully validated at any useful significance level.

**Validation budget depends on WHICH TEST is the binding gate**:

| Test | Effective N | K_max at Δ=0.30, 80% power | Comment |
|------|------------|---------------------------|---------|
| Trade-level paired test | 188 trades | Potentially large (>50) | High power per test |
| WFO Wilcoxon (8 folds) | 8 folds | **1-3** (power < 50% at K=1!) | Current binding gate |
| Bootstrap CI | 1000 resamples | Intermediate | Point estimate strong, comparison weak |

**The WFO bottleneck is REAL**: E5-ema21D1 has WFO p=0.125 > α=0.10 →
HOLD verdict. The algorithm works but the test cannot confirm it at N=8
folds. This is the ACTUAL binding constraint, not a theoretical concern.

**K_max is an EMPIRICAL question**: The exact budget capacity cannot be
determined from spec alone. A power simulation study using the project's
real test statistics, data, and effect sizes is needed to calibrate K_max.

**Why the loop is human-AI, not fully automated**: With tight budget, K must
be kept small. Human domain judgment is a practical filter (reduce ~200
pre-filter survivors to ~3-10 for formal testing). The claim that human
intuition has inherent competitive advantage is plausible but unproven —
it is a design assumption, not an established fact.

**Proposal**: Explicit statistical budget accounting as a first-class framework
component, integrated with the discovery loop and validation pipeline.

### Budget model

```
StatisticalBudget:
  dataset_params:
    n_trades: int               # Available trades for validation
    timespan_years: float       # Calendar time coverage
    m_eff: float                # Nyholt effective DOF
  budget:
    alpha_fwer: float           # Family-wise error rate (default: 0.05)
    k_tested: int               # Features formally tested so far
    k_max_estimate: int         # Estimated max at min_detectable_effect
    min_detectable_effect: float # Minimum Δ_Sharpe for 80% power at current k
  ledger: list[BudgetEntry]     # Audit trail of every test
```

### Two-tier screening: pre-filter (reduced cost) vs formal test (full cost)

| Tier | Activity | Budget cost | Purpose |
|------|----------|-------------|---------|
| **Tier 0: Pre-filter** | MI ranking, top-N selection, DFL-06 analyses | **Reduced** — see below | Reduce candidate pool from ~140K to ~200 |
| **Tier 1: Formal test** | DFL-08 Stage 5 validation, WFO, bootstrap CI | **Full — 1 unit** per feature tested | Rigorous validation with error control |

**Tier 0 is NOT free**: MI screening introduces selection bias because MI and
Sharpe are correlated (both measure the feature-return relationship through
different lenses). Features selected by high MI are more likely to have high
Sharpe under H0, inflating Tier 1 false positive rates.

**What Tier 0 achieves**: The practical value is reducing Tier 1 test count
from ~140K to N (e.g., 200). Holm correction at Tier 1 applies over N tests,
not 140K. This is "much cheaper" — not "free."

**How to handle the selection bias**: Two approaches (debate should decide):

1. **Permutation calibration**: Compute MI on permuted returns (1000×). Use
   the permutation-null MI distribution to set a threshold that accounts for
   the screening effect. Computationally expensive.
2. **Conservative inflation factor**: Apply a multiplier (e.g., 2×) to Tier 1
   α to compensate for MI-Sharpe correlation. Calibrate empirically via
   simulation.

**The exact cost of Tier 0 is an EMPIRICAL question**: Requires a simulation
study — generate synthetic features with known properties, run the two-tier
pipeline, measure actual vs nominal false positive rate. This is a CODE task,
not a spec task.

### Budget lifecycle within DFL-08 graduation path

```
DFL-06 Analysis (10 analyses)
  │  [Zero formal units — data profiling, process observations]
  ▼
DFL-08 Stage 1: Discovery → Candidate
  │  Tier 0 pre-filter: top-N by MI rank (N declared before screening)
  │  [Zero formal units — selection bias acknowledged]
  ▼
DFL-08 Stage 2: Candidate → Deep Dive Report
  │  Distributional analysis, null model test, redundancy
  │  [Zero formal units — characterization, not formal test]
  ▼
DFL-08 Stage 3: Report → Human Decision
  │  Human reviews, decides: INVESTIGATE / TEMPLATE / GRAMMAR / DISCARD
  │  [Zero formal units — human judgment]
  ▼
DFL-08 Stage 4: Human Decision → Feature Registry
  │  Feature registered with provenance
  │  [NO budget cost — registration is bookkeeping]
  ▼
DFL-08 Stage 5: Registry → Strategy Validation
  │  Full validation: WFO, bootstrap, 7 gates
  │  [COSTS 1 BUDGET UNIT — this is the formal test]
  │
  │  Budget check BEFORE running validation:
  │    if budget.k_tested >= budget.k_max_estimate:
  │      WARN: "Budget exhausted. Validation will have <50% power.
  │             Consider: (a) collect more data, (b) accept lower power,
  │             (c) human override with explicit justification."
  │
  ▼
Budget ledger updated: k_tested += 1, min_detectable_effect recalculated
```

### Budget accounting rules

1. **Pre-filter = zero formal budget units (selection bias acknowledged)**:
   DFL-06 analyses, MI screening, IC ranking, DFL-07
   Phase 1-2 — all zero budget cost. These are characterization, not decisions.

2. **Formal test costs 1 unit**: Each feature that enters full validation
   (DFL-08 Stage 5) consumes 1 budget unit. The Holm correction adjusts
   α for all k_tested features.

3. **Human override allowed**: If budget is exhausted, human researcher
   (Tier 3 authority) may authorize additional tests with explicit
   justification and acknowledged reduced power. Override is recorded in ledger.

4. **Budget is per-dataset**: When new data arrives (Phase 2 clean OOS or
   Phase 3 new research), budget resets because N_trades increases.
   Budget from previous dataset is archived for audit.

5. **Budget is SEPARATE from grammar scan**: Topic 013 SSE-09 Holm correction
   applies to grammar_depth1_seed scan (50K+ configs). Discovery loop features
   have their own budget. Rationale: grammar scan tests within a DECLARED
   space (known combinatorial structure). Discovery loop tests NOVEL features
   (unknown space). Pooling would either (a) exhaust grammar budget with
   discovery features or (b) penalize discovery features for grammar's
   combinatorial explosion.

6. **Redundancy deduction**: If a new feature correlates r > 0.95 with an
   already-tested feature (behavioral equivalence per Topic 013 SSE-04-THR),
   it does NOT consume a new budget unit — it's treated as a variant of the
   existing test. This prevents redundant features from wasting budget.

### Current budget estimate for btc-spot-dev

```
Dataset: BTC/USDT 2017-08 → 2026-02 (H4+D1, harsh 50bps)
N_trades = 188, M_eff = 4.35, WFO folds = 8
```

**Retroactive counting (open question)**:

Pre-framework research (x0-x32) tested many features, but NOT under the
framework's budget rules. Two options:

| Option | What counts | K_tested | Rationale |
|--------|-----------|----------|-----------|
| **Clean start** | Only tests under the framework | 0 | Pre-framework methodology was different. Honest fresh start |
| **Full accounting** | ALL features ever tested | ~28+ (incl. 22 rejected) | Most conservative. But retroactive FWER invalidates VDO (p=0.031 > 0.05/28) |

**Neither option is satisfying**: Clean start ignores real tests. Full
accounting retroactively fails known-good features. This is a DESIGN DECISION
for debate, not a mathematical derivation.

**The binding constraint is WFO power, not K**:

Even at K=1, WFO Wilcoxon with 8 folds has power < 50% for Δ_Sharpe = 0.30.
E5-ema21D1 has p=0.125 — the test cannot confirm an algorithm that WORKS.
Adding more features (K > 1) makes this worse, but the constraint is already
binding at K=1.

**K_max requires a power simulation study**: The exact budget capacity depends
on the test statistic, effect size distribution, and data properties. A
simulation study using the project's real WFO setup with synthetic features
is needed. This is a CODE task.

**Implication**: The budget tracker makes the ceiling VISIBLE. But the ceiling
itself is determined empirically, not by spec. v2's value is in making the
constraint explicit and designing the two-tier pipeline around it.

### Interaction with existing findings

| Finding | Interaction |
|---------|------------|
| DFL-06 | 10 analyses → all Tier 0 (zero formal units). Produces candidates, not decisions |
| DFL-07 | Phase 1-2 methodology → Tier 0. Phase 3 WFO → Tier 1 (costs budget) |
| DFL-08 | Stage 1-4 → Tier 0. Stage 5 → Tier 1. Budget check before Stage 5 |
| DFL-09 | Scope clarification: non-OHLCV analysis is Tier 0 (zero formal units) |
| DFL-10 | Stage 2.5 data profiling → Tier 0 (zero formal units). Informs grammar design |
| DFL-01 | AI analysis layer → Tier 0 (observation, not decision) |
| DFL-04 | Contamination: budget ledger is a process artifact, not answer prior |
| SSE-09 (013) | Grammar scan uses separate Holm budget. Discovery loop = disjoint |
| F-08 (006) | Registry must record `budget_entry_id` for audit trail |

### Open questions

- Is the budget separation (grammar vs discovery) correct? Or should all
  tests be pooled into one family? Pooling is more conservative but may
  make grammar scan impractical (50K configs + discovery features).
- Should the ~6 features already tested in x0-x32 be retroactively counted
  in the budget? If so, current budget is already partially consumed.
  Argument for: honest accounting. Argument against: those tests used
  different methodology (pre-framework), not apples-to-apples.
- What happens when budget is exhausted but a promising feature exists?
  Options: (a) wait for more data, (b) human override with reduced power
  acknowledged, (c) accept lower α_FWER for new features.
- Should the budget model account for CORRELATED features (effective number
  of independent tests < k_tested)? Nyholt M_eff could apply to feature
  space, not just timescale space.
- BudgetEntry schema: what metadata per test? Minimum: feature_id, test_date,
  test_metric, p_value, effect_size, verdict, holm_adjusted_alpha.

---

## DFL-12: Grammar Depth-2 Composition

- **issue_id**: X38-DFL-12
- **classification**: Thiếu sót
- **opened_at**: 2026-03-31
- **opened_in_round**: 0
- **current_status**: Open

**Motivation**:

v1 grammar (SSE-D-02, Topic 018 CLOSED) is depth-1: `feature = f(field, lookback)`.
This captures single indicators (ema, sma, std, atr) but NOT compositions — features
that combine two depth-1 features through an operator.

VDO is a composition: `ratio(ema(taker_buy_vol, 14), ema(total_vol, 14))`. Under
v1, VDO cannot be expressed in grammar — it entered via human insight. But the
formula itself is a depth-2 composition of two depth-1 features through a `ratio`
operator. If grammar supported depth-2, VDO's formula (though not the CONCEPT)
would be in the search space.

**The gap**: No finding in Topic 019 proposes depth-2 composition. DFL-03 discusses
grammar extension as "new building blocks for grammar_depth1_seed" (adding
primitives like `volume_ratio`). DFL-09 clarifies scope (analysis vs ideation).
Neither proposes NEW COMPOSITION OPERATORS that create features from EXISTING
features. This is a qualitatively different kind of grammar expansion.

**Proposal**: Add composition operators to the grammar, creating depth-2 features.

### Composition operators

| Operator | Signature | Example |
|----------|-----------|---------|
| `ratio` | (Series, Series) → Series | `ratio(ema(close,21), ema(close,50))` |
| `diff` | (Series, Series) → Series | `diff(ema(close,21), sma(close,50))` |
| `zscore` | (Series, int) → Series | `zscore(ema(close,21), 20)` |
| `rank` | (Series, int) → Series | `rank(std(close,14), 50)` |

**Excluded operators**:
- `crossover`: produces BoolSeries (signal), not composable Series
- `lag`: redundant with lookback parameter extension

### Search space impact

Depth-2 DRAMATICALLY expands the grammar search space:

| Grammar level | Fields | Estimated configs |
|---------------|--------|-------------------|
| Depth-1 (v1) | 5 OHLCV | ~300 |
| Depth-2, binary (ratio, diff) | 5 OHLCV | ~135,000 |
| Depth-2, unary (zscore, rank) | 5 OHLCV | ~6,000 |
| **Total depth-2 (OHLCV)** | 5 | **~140,000** |

**Derivation** (binary operators):
- Depth-1 base features: 6 ops × 5 fields × 10 lookbacks = 300
- `ratio` (non-commutative): 300 × 299 = 89,700 ordered pairs
- `diff` (anti-symmetric): C(300,2) = 44,850 unordered pairs
- Total binary: ~135,000 (before structural pruning)

This is a ~460× expansion from depth-1. The entire pre-filter design (DFL-11
Tier 0) and budget model (DFL-11) exist to make this tractable.

### SSE-D-02 interaction

Depth-2 composition operates WITHIN the OHLCV-only constraint (SSE-D-02 rule 3).
Composition operators combine OHLCV-derived features — they do not introduce new
input fields. `ratio(ema(close,21), ema(volume,14))` uses close and volume, both
OHLCV fields.

**However**, the combinatorial explosion from ~300 to ~140,000 features raises a
SPIRIT-of-the-law question: SSE-D-02's OHLCV-only rule was designed to prevent
search space explosion. Depth-2 achieves explosion WITHIN OHLCV. Does this violate
the intent of SSE-D-02 even though it satisfies the letter?

### Pruning strategy

~140K features contain structural redundancies:
- Self-compositions: `ratio(f, f)` = constant → remove
- Degenerate lookbacks: `zscore(ema(close,3), 3)` → near-constant → remove
- Expected reduction via structural pruning: ~140K → ~80-100K
- Further reduction via DFL-11 Tier 0 MI ranking: → top-200

### Key design decision for debate

**The central question**: Should v2 grammar support depth-2 composition?

| Option | Search space | VDO expressible? | Budget impact | Risk |
|--------|-------------|-------------------|---------------|------|
| **A: YES, depth-2 in grammar** | ~140K (OHLCV-only) | Formula yes, but OHLCV-only fields | Pre-filter required (DFL-11) | Combinatorial explosion vs budget |
| **B: NO, depth-2 via human template only** | ~300 (grammar) + unlimited (human) | Only via human insight | No grammar budget impact | Human bottleneck |
| **C: YES, but depth ≤ 2 and operator whitelist** | ~140K with pruning | Formula yes, OHLCV-only | Bounded expansion | Requires operator review |

Option B is the status quo (v1). Option A/C extend grammar. The debate must
decide whether the ~460× expansion is justified given the statistical budget
constraints identified in DFL-11.

### Interaction with other findings

| Finding | Interaction |
|---------|------------|
| DFL-03 | Grammar extension channel 2. DFL-12 is a SPECIFIC extension (operators, not primitives) |
| DFL-08 | Stage 1 input: grammar depth-2 output feeds into graduation pipeline |
| DFL-09 | Scope: depth-2 composition within OHLCV satisfies SSE-D-02 letter, but spirit? |
| DFL-11 | Budget: ~140K features → pre-filter essential. Budget K_max constrains formal testing |
| SSE-D-02 (018) | OHLCV-only: composition uses only OHLCV fields, but search space explodes |
| F-08 (006) | Feature registry: depth-2 features need `generation_mode: grammar_depth2` |

### Open questions

- Does depth-2 within OHLCV violate the SPIRIT of SSE-D-02, even though it
  satisfies the letter? If so, should 018 be reopened?
- Should the operator whitelist be fixed in the spec or extensible by debate?
- Is depth-2 sufficient, or will depth-3 eventually be needed? If depth-3 is
  foreseeable, should the design account for it now (general recursion) or later?
- Should depth-2 generation be deterministic (enumerate all) or sampled
  (random subset) to manage compute cost?

---

## DFL-13: Data Trustworthiness & Cross-Source Validation

- **issue_id**: X38-DFL-13
- **classification**: Thiếu sót
- **opened_at**: 2026-03-31
- **opened_in_round**: 0
- **current_status**: Open

> **Debate scope note**: DFL-13 addresses a layer BELOW statistical analysis —
> whether the raw numbers themselves are trustworthy. Without this foundation,
> DFL-06's 10 analyses and DFL-10's Stage 2.5 profiling operate on potentially
> corrupted inputs. The architecture question: should the framework include a
> data trustworthiness assessment step, and what is its scope?

**Motivation**:

Stage 2 (Data audit, F-05) checks data INTEGRITY: gaps, duplicates, checksums,
anomaly disposition. DFL-10 Stage 2.5 profiles STATISTICAL properties:
distributions, pairwise dependencies, temporal structure. Both assume the
underlying numbers are ACCURATE — that `volume = 15,000 BTC` means 15,000 BTC
actually traded, and `taker_buy_base_vol = 8,000` means 8,000 BTC were bought
by takers.

This assumption is unverified and potentially wrong for crypto exchange data.

**Three categories of data trustworthiness risk**:

### Category A: Exchange-reported metric reliability

Binance reports `volume`, `taker_buy_base_vol`, `taker_buy_quote_vol`, and
`num_trades` per bar. These are exchange-computed aggregates with opaque
methodology:

| Field | Risk | Impact if compromised |
|-------|------|----------------------|
| `volume` | Wash trading inflates volume on crypto exchanges. Bitwise 2019 SEC filing found ~95% of reported BTC volume on 81 surveyed exchanges was fabricated — though Binance was among the ~10 exchanges Bitwise classified as LEGITIMATE. The concern is not that Binance is known to wash-trade, but that exchange-reported volume is OPAQUE and independently unverified for this dataset | VDO filter uses volume as denominator. If volume includes non-economic activity (wash trades, internal transfers), VDO ratio is distorted → entry signal affected |
| `taker_buy_base_vol` | Binance's taker/maker classification is proprietary. Self-trade (same entity on both sides) classified how? | DFL-06 Analysis 1 derives 6 features from taker fields. All compromised if classification is wrong |
| `num_trades` | May count internal matching engine operations, not independent economic decisions | `avg_trade_size`, `trade_intensity`, `volume_per_trade` (DFL-06 derived features) all use num_trades |
| `quote_volume` | Should equal sum(price × qty) per trade. Rounding, fee inclusion, or aggregation errors possible | `taker_buy_premium`, `quote_per_base` derived features affected |

**Evidence from btc-spot-dev**: X27 EDA noted volume peaked ~24K BTC/bar in
2022 then dropped to ~3,500-5,900 by 2024-2026. X27 Obs27 attributed this to
market microstructure changes (ETF launch shifting volume to CME/spot ETFs).
This is a plausible explanation, but it is an INTERPRETATION — the raw data
cannot distinguish between (a) genuine volume migration to other venues,
(b) Binance reporting methodology change, or (c) reduced wash-trading after
regulatory pressure. Cross-exchange validation (Category B) would distinguish
these explanations.

### Category B: Cross-exchange validation

If Binance data is trustworthy, similar patterns should appear on independent
exchanges (Coinbase, Bybit, OKX) for the same timestamps. Divergences indicate
exchange-specific artifacts vs genuine market properties.

**Specific tests**:
- Same-timestamp volume correlation: Binance volume vs Coinbase volume at H4.
  High correlation (ρ > 0.9) → volume reflects real market activity.
  Low correlation → exchange-specific noise or wash trading
- Taker ratio comparison: Does `taker_buy_ratio` on Binance track similarly on
  exchanges that use different matching engines?
- Price-volume relationship: Does the Amihud ratio (DFL-06 Analysis 10) have
  similar magnitude and dynamics across exchanges?
- `num_trades` scaling: If Binance reports 50K trades/H4 bar and Coinbase reports
  5K, the ratio should be roughly proportional to market share. Deviations
  indicate counting methodology differences

**Data requirement**: This is the ONLY DFL finding that requires data NOT in the
current CSV. Cross-exchange comparison requires downloading equivalent OHLCV+
taker data from 2-3 other exchanges for the same period. This is a ONE-TIME
validation exercise, not ongoing pipeline input.

### Category C: ETL pipeline correctness (overlaps Stage 2)

The data pipeline (`/var/www/trading-bots/data-pipeline/`) transforms Binance
API responses into parquet files (`/var/www/trading-bots/data-pipeline/output/`).
Some of these checks overlap with
Stage 2 (integrity audit), but are included here because aggregation-level
errors may not be caught by Stage 2's gap/duplicate/checksum tests:

- Aggregation correctness: 15m → H1 → H4 → D1 aggregation. Is volume SUMMED
  correctly? Is high = MAX(sub-bar highs)? Is open = FIRST sub-bar open?
- Missing bar handling: if a 15m bar is missing, how does H4 aggregation handle
  the gap? (Stage 2 catches missing bars, but not aggregation errors AROUND gaps)
- Historical data consistency: has Binance retroactively adjusted any historical
  bars? (Some exchanges do this for erroneous trades)

**Specific validation** (one-time, may belong in Stage 2 scope):
- Download raw 15m bars for a random 30-day window. Manually aggregate to H1,
  H4, D1. Compare with existing CSV values. Zero tolerance for discrepancies
  in OHLC. Volume aggregation within 0.1% tolerance (rounding)

**Note**: Category C may be better handled as an extension of Stage 2 (integrity
audit) rather than a separate trustworthiness concern. The debate should decide
whether aggregation correctness is an integrity question (Stage 2) or a
trustworthiness question (DFL-13).

**Proposal**: A one-time data trustworthiness assessment covering exchange
metric reliability (Category A), cross-exchange validation (Category B), and
ETL correctness (Category C). The framework should either include this as a
stage or explicitly document the assumption that exchange-reported data is
accurate.

### Interaction with existing findings

| Finding | Interaction |
|---------|------------|
| DFL-06 | Analyses 1, 5, 9, 10 depend on volume/taker fields. If Category A risk is real, these analyses operate on potentially corrupted inputs |
| DFL-10 | Stage 2.5 profiles statistical properties — complements trustworthiness (DFL-13 validates accuracy, DFL-10 profiles distribution) |
| DFL-14 | DGP change detection (Layer 2) runs on volume/taker fields. If those fields are untrustworthy (Category A), detected structural breaks may be data artifacts rather than genuine DGP changes |
| DFL-15 | Data acquisition scope. Category B requires cross-exchange data — DFL-15 scopes whether external data acquisition is in framework |
| DFL-17 | Protocol 3 (VDO reconstruction) uses taker_buy_base_vol. If taker classification is unreliable (Category A), Protocol 3 calibration is affected |
| DFL-18 | Volume regime definitions (Type 2) use rolling volume. If volume is inflated in some periods, regime boundaries are shifted |
| F-05 (003) | Stage 2 integrity audit. Category C overlaps — debate should assign ownership |

### What this is NOT

| Concern | Answer |
|---------|--------|
| "Replaces Stage 2 integrity audit" | No. Stage 2 = gaps/duplicates/checksums. DFL-13 Categories A+B = are the NUMBERS accurate and representative? Different layer. Category C may overlap — see note above |
| "Requires continuous cross-exchange monitoring" | No. One-time validation exercise. If Binance data passes, proceed. If it fails, document which fields are unreliable |
| "Blocks all analysis until validated" | Judgment call. Cross-exchange validation could run in parallel with DFL-06 analyses. Results calibrate confidence, not block work |

### Architecture decision for debate

| Decision | Alternatives | Implication |
|----------|-------------|-------------|
| Should trustworthiness assessment be a framework stage? | (a) Yes, Stage 1.5 between lock and audit (b) Part of Stage 2 (c) One-time validation, not in pipeline | (a) adds overhead every campaign. (b) overloads Stage 2. (c) cheapest but no repeat validation |
| Cross-exchange data: acquire or not? | (a) Acquire for validation (b) Document as assumption, skip | (a) costs time. (b) accepts risk |

**Open questions**:
- If Binance volume IS significantly inflated by wash trading, which DFL-06
  analyses are salvageable? (OHLC prices should be unaffected — only volume-
  derived features are at risk)
- Should the framework require cross-exchange validation for EVERY new asset,
  or only for the first campaign (BTC)?
- Is there a way to detect wash trading from the data itself (e.g., unusual
  round-number volume concentrations, perfectly symmetric buy/sell) WITHOUT
  cross-exchange data?
- How does this interact with DFL-10 Stage 2.5? Should `data_profile.json`
  include a trustworthiness section, or is that a separate artifact?

---

## DFL-14: Non-Stationarity Protocol — DGP Change Detection & Feature Shelf-Life

- **issue_id**: X38-DFL-14
- **classification**: Thiếu sót
- **opened_at**: 2026-03-31
- **opened_in_round**: 0
- **current_status**: Open

> **Debate scope note**: DFL-06 Analysis 7 + DFL-07 A5 already provide detection
> TOOLS (PELT, CUSUM, rolling metrics) for non-stationarity — including structural
> breaks. DFL-14 provides the RESPONSE PROTOCOL: how to interpret detected breaks,
> what framework-level actions follow, and how to classify features by prospective
> validity. DFL-14's value is governance (what to DO), not method (how to DETECT).

**Motivation**:

BTC/USDT 2017-08 → 2026-02 spans multiple market microstructure regimes:

| Period | Market characteristic | Data implication |
|--------|---------------------|------------------|
| 2017-2018 | Retail-dominated, high volatility, ICO era | High volume, high num_trades, extreme taker imbalance |
| 2019-early 2020 | Post-crash, low volatility, consolidation | Low volume, compressed spreads, fewer trades |
| mid-2020-2021 | DeFi Summer (mid-2020), institutional entry (MicroStrategy Aug 2020, Tesla Feb 2021), bull market | Volume surge, changed participant composition, DeFi cross-venue flows |
| 2021-2022 | Peak → crash, Terra/Luna, FTX collapse | Extreme events, structural breaks in correlations |
| 2023-2024 | ETF approval, halving, institutional dominance | Different volume profile, lower retail participation |
| 2024-2026 | Post-ETF, mature market structure | Potentially different DGP from earlier periods |

A feature discovered in 2017-2019 data may not exist in 2024-2026 data — not
because the feature "decayed" (gradual) but because the DATA GENERATING PROCESS
changed (structural).

DFL-06 Analysis 7 + DFL-07 A5 together provide TOOLS for detecting both gradual
decay (rolling Sharpe, alpha regression) AND structural breaks (DFL-07 A5
lists PELT and CUSUM as applicable to Analyses 5, 7, and 10). What is MISSING
is not the detection capability but the RESPONSE PROTOCOL: what to do when a
break is detected, how to classify features by prospective validity, and how
to distinguish DGP-level changes from strategy-level changes.

**Three types of non-stationarity (all detectable by Analysis 7 + DFL-07 A5,
but requiring different RESPONSES)**:

| Type | Characteristic | Example | Required response |
|------|---------------|---------|-------------------|
| Signal decay | Gradual, continuous, partial | Strategy Sharpe declining 0.05/year | Monitor. May stabilize |
| DGP structural break | Sudden, discrete, complete | Taker classification methodology change | Feature definition itself may be invalid |
| Regime shift | Cyclical, recurring, bounded | Bull → bear cycle | Feature may return. Design for regime-conditioning |

Analysis 7 can detect all three (using PELT for structural breaks, rolling
metrics for gradual decay). But the INTERPRETATION and FRAMEWORK-LEVEL ACTION
differ fundamentally — and no existing finding provides that response protocol.

**Proposal**: A three-layer non-stationarity protocol integrated with the
discovery loop and validation pipeline.

### Layer 1: Known exogenous events registry

Maintain a list of KNOWN market structure changes with dates:

| Event type | Examples | Data impact |
|------------|---------|-------------|
| Exchange-level | Fee structure changes, new order types, matching engine upgrades | Volume, num_trades, spread proxy affected |
| Regulatory | ETF approval, country bans, reporting requirements | Participant composition, volume patterns |
| Market structure | New derivative products (perps, options), DeFi emergence | Cross-venue flow, funding rate effects |
| Asset-level | Halvings, major protocol upgrades | Supply dynamics, narrative cycles |
| Crisis events | Exchange collapses (FTX), stablecoin depegs (UST) | Correlation regime breaks, liquidity shocks |

**Purpose**: When DFL-06 analyses find a structural break, check against the
registry. If the break aligns with a known event, the break is EXPLAINED
(not mysterious). Explained breaks inform feature design: "this feature
works except during exchange crises" is useful information.

**Scope**: The registry is a REFERENCE DOCUMENT, not a gate. It does not block
analysis or invalidate features. It provides context for interpretation.

### Layer 2: Automated DGP change detection

Apply DFL-07 A5 change-point methods (PELT, CUSUM, Bai-Perron) not just to
individual features but to RELATIONSHIPS between features:

**What to monitor for structural breaks**:

| Metric | What it detects | Method |
|--------|----------------|--------|
| Rolling correlation matrix eigenvalues | Change in correlation structure (not just levels) | PCA on rolling windows, track eigenvalue trajectory |
| Volume / num_trades ratio | Change in average trade size (institutional vs retail) | PELT change-point on rolling ratio |
| Taker_buy_ratio distribution | Change in market participant behavior | KS test on rolling windows vs full-sample |
| Intraday volume profile (if H1 data used) | Change in when volume occurs (timezone/participant shift) | Cosine similarity of hourly volume profiles across years |
| Feature-return IC stability | Change in which features carry information | Rolling IC for top features, detect IC sign-flips |

### Layer 2 → Layer 3 handoff

Layer 2 output: a dated regime segmentation (list of DGP regime boundaries
with dates and characterization). This is a formal artifact that Layer 3
consumes as input.

When Layer 2 detects a break NOT in Layer 1's registry (unexplained break):
the break is flagged as `UNEXPLAINED` in the segmentation. Layer 3 still uses
it for classification — an unexplained break is still a real change-point,
even without a causal story. The registry (Layer 1) provides context for
interpretation, not a filter on which breaks "count."

**Degenerate case — zero breaks detected**: If PELT/CUSUM find no change-points,
the segmentation is a single regime spanning the full sample. Layer 3 would
classify all features as STRUCTURAL by default (they pass "across ALL regimes"
trivially). This is potentially misleading — no breaks may mean the test is
underpowered, not that the DGP is truly stationary. This case should be flagged:
if zero breaks are detected, Layer 3 reports `DGP_REGIME_COUNT = 1 (SINGLE)`,
and the STRUCTURAL classification carries a caveat that it is based on a single-
regime segmentation.

### Layer 3: Feature shelf-life assessment

For every feature that passes DFL-08 Stage 2 (deep dive), assess prospective
validity using Layer 2's regime segmentation:

**Shelf-life classification**:

| Class | Definition | Test | Action |
|-------|-----------|------|--------|
| **STRUCTURAL** | Feature works across ALL DGP regimes AND shows no gradual decay | Exists across ALL Layer 2 regimes AND rolling feature-return IC (computed per DFL-07 A2 methods) has no significant negative trend | Long shelf-life. STILL REQUIRES periodic monitoring (gradual decay below break-detection threshold is possible) |
| **REGIME-DEPENDENT** | Feature works in some DGP regimes but not others | Performance varies significantly (KS p < 0.05) across Layer 2 regimes, but IC > 0 in at least one regime | Medium shelf-life. Requires regime identification in production |
| **EPOCH-SPECIFIC** | Feature exists only in a specific historical period | Structural break in feature-return relationship. Post-break IC ≈ 0. No regime where feature works post-break | Short shelf-life. WARN: may not exist in future data |

**Overlap handling**: A feature can be BOTH regime-dependent AND epoch-specific
(e.g., works in bull regimes, but only pre-2022). When classes overlap, the
MORE RESTRICTIVE class applies (EPOCH-SPECIFIC > REGIME-DEPENDENT > STRUCTURAL).

**Integration with DFL-08 graduation path**:

- Stage 2 deep dive MUST include shelf-life classification (note: DFL-08 Stage 2
  already requires "structural break detection" as a gate — DFL-14 extends this
  with the named classification and DFL-02 report integration)
- EPOCH-SPECIFIC features get a WARNING flag in DFL-02 report — human decides
  whether to proceed (may be valid if the epoch is ongoing)
- REGIME-DEPENDENT features require a regime identification mechanism in the
  strategy that uses them (consistent with existing EMA(21d) regime filter design)

**Relationship to DFL-18**: DFL-18 (regime-conditional profiling) provides an
independent EMPIRICAL measurement of feature × regime interaction. DFL-14 Layer 3
provides CLASSIFICATION based on DGP change detection. The two use different
methods (DFL-18: IC across hand-defined regimes; DFL-14: IC across DGP-detected
regimes) and may produce different answers. When they conflict, the debate
should determine which takes precedence — or whether both classifications
are recorded as metadata for human judgment.

### Interaction with existing findings

| Finding | Interaction |
|---------|------------|
| DFL-06 Analysis 7 | Analysis 7 + DFL-07 A5 provide detection TOOLS (PELT, CUSUM, rolling metrics). DFL-14 provides the RESPONSE protocol (classification, actions) |
| DFL-07 A5 | Change detection methods applied to DGP-level relationships (Layer 2), not just strategy-level signals |
| DFL-08 Stage 2 | Shelf-life classification extends Stage 2's existing "structural break detection" gate with named classes and DFL-02 integration |
| DFL-10 Stage 2.5 | `data_profile.json` could include DGP regime count as a field |
| DFL-11 | Epoch-specific features: should they consume budget if shelf-life is short? |
| DFL-13 | If data fields are unreliable (Category A), Layer 2 DGP detection on those fields is compromised |
| DFL-18 | Complementary regime profiling. DFL-14 = DGP-detected regimes + classification. DFL-18 = hand-defined regimes + stability score. May produce different answers — resolution needed |
| Topic 013 (SSE-04) | Convergence analysis: DGP breaks across campaigns need special handling in convergence thresholds |

**Open questions**:
- Layer 1 registry: who maintains it? Human (manual updates) or automated
  (news API, exchange changelog scraping)? Manual is more reliable, automated
  is more complete
- Layer 2 frequency: run DGP change detection once per campaign, once per
  session, or continuously? Tradeoff: more frequent = more responsive,
  but adds compute and analysis overhead
- Should EPOCH-SPECIFIC features be automatically excluded from grammar
  (preventing automated generation of potentially expired features)?
  Or is human judgment sufficient?
- How does this interact with Clean OOS (NV2)? If fresh data is from a
  NEW DGP regime, a strategy validated on old data may fail not because
  the strategy is wrong but because the market changed. How to distinguish?

---

## DFL-15: Resolution Gap Assessment & Data Acquisition Scope Decision

- **issue_id**: X38-DFL-15
- **classification**: Judgment call
- **opened_at**: 2026-03-31
- **opened_in_round**: 0
- **current_status**: Open

> **Debate scope note**: DFL-15 is primarily a SCOPE DECISION — what data the
> framework considers in-scope and out-of-scope, and the explicit rationale.
> The architecture question: should the framework define a data acquisition
> policy, or treat available data as exogenous input?

**Motivation**:

DFL-06 Analyses 1-10 exhaustively explore the existing 13-field CSV at 4
resolutions (15m, H1, H4, D1). But the CSV is a SUBSET of available market data.
The framework currently has no explicit decision about what data is in scope.

**Data resolution hierarchy — what exists vs what's available**:

```
Tick-by-tick (Binance WebSocket)
  │  Content: every individual trade (price, qty, taker side, timestamp_ms)
  │  Volume: ~500K-2M trades/day for BTCUSDT
  │  Status: NEVER acquired. Not in data pipeline.
  │
  ├──→ 1-second bars (aggregated from ticks)
  │     Status: NEVER acquired
  │
  ├──→ 1-minute bars (Binance kline API)
  │     Status: NEVER acquired
  │
  ├──→ 15-minute bars ← CURRENT FLOOR (299,755 rows)
  │     13 fields including volume, taker_buy, num_trades
  │
  ├──→ H1 bars (74,953 rows) ← Available, UNUSED in strategies
  │
  ├──→ H4 bars ← PRIMARY strategy resolution
  │
  └──→ D1 bars ← Used only for regime filter
```

**What's invisible at 15m resolution**:

| Pattern | Visible at tick/1s? | Visible at 15m? | Impact |
|---------|--------------------|--------------------|--------|
| Bid-ask spread | Yes (from tick data) | No (OHLC only) | True transaction cost invisible |
| Order flow imbalance within bar | Yes (trade-by-trade) | Partial (taker_buy_ratio is aggregate) | Intrabar flow dynamics lost |
| Trade arrival rate clustering | Yes (inter-trade times) | No (aggregated to num_trades) | Hawkes process, market maker detection invisible |
| Flash crashes / wicks | Partial (1s bars capture) | Partial (high/low capture extremes but not duration) | Sub-bar liquidity events |
| VWAP deviation from close | Yes (trade-weighted) | Partial (quote_volume/volume ≈ VWAP) | Price impact asymmetry within bar |

**What's available but not in the CSV at all**:

| Data type | Source | Relevance | Acquisition difficulty |
|-----------|--------|-----------|----------------------|
| Funding rates | Binance Perps API | Crowded trade proxy. F4 hypothesis (DFL-07). Currently only taker_ratio as proxy | Easy — API available, historical data downloadable |
| Open interest | Binance Perps API | Position buildup / unwind. Leverage indicator | Easy — same API |
| Order book snapshots | Binance API (not historical) | Depth, resilience, real spread | Hard — no historical, must collect going forward |
| On-chain metrics | Glassnode / CryptoQuant API | Whale flows, exchange reserves, miner behavior | Medium — paid API, different format |
| Liquidation data | Binance/Bybit API | Forced selling/buying events | Medium — historical availability varies |
| Macro indicators | FRED / Yahoo Finance | DXY, rates, VIX — macro regime context | Easy — free, well-documented APIs |

### The scope decision

This finding does NOT propose acquiring all this data. It proposes that the
framework make an EXPLICIT scope decision — a documented boundary — rather than
operating on an implicit assumption that the 13-field CSV is sufficient.

**Options for debate**:

| Option | Scope | Rationale | Risk |
|--------|-------|-----------|------|
| **A: Current data only** | 13 fields, 4 resolutions (15m/H1/H4/D1) | Simplicity. DFL-06 shows unexploited fields exist. Exhaust current data before adding more | May miss patterns that require finer resolution or different data types |
| **B: Current + funding rates + OI** | 15 fields, same resolutions | Low acquisition cost. Funding + OI are the two most commonly cited crypto-specific signals | Adds complexity. Two new fields may not justify pipeline changes |
| **C: Current + tick data for validation** | 13 fields + tick data for DFL-13 cross-validation and Roll's spread estimation | Tick data validates 15m aggregation accuracy and enables true microstructure tests | Large data volume (100s of GB). Processing infrastructure needed |
| **D: Explicit boundary document** | Whatever data is available when pipeline runs | Framework is data-agnostic — it profiles and analyzes whatever it receives (DFL-10 + DFL-06). No scope restriction in spec | Cleanest architecturally. But no guidance on what to acquire |

**Recommendation toward hybrid**: The framework ARCHITECTURE should be
data-agnostic at the spec level (accept any fields, profile all, analyze all
per DFL-06/10 — Option D). But each CAMPAIGN should declare its data boundary
at protocol lock (Stage 1), including a minimum required field set for that
campaign and explicit justification for any excluded available fields. This is
a two-level design: agnostic architecture, bounded campaign.

### Roll's realized spread estimator

Roll (1984) showed that serial covariance of price changes estimates effective
bid-ask spread: `spread = 2 × sqrt(-Cov(Δp_t, Δp_{t-1}))` when Cov < 0.

**Resolution dependency**: Roll's model relies on bid-ask bounce — the
negative serial correlation caused by trades alternating between bid and ask
prices. This operates at tick-to-tick frequency (milliseconds). At H4
resolution (~500K-2M trades per bar), the bid-ask component is completely
overwhelmed by genuine price dynamics. The literature (Hasbrouck 2009) shows
Roll's estimator degrades sharply even at 5-minute resolution.

**Implication for DFL-06 Analysis 10**: Roll's spread estimator CANNOT be
meaningfully applied to existing H4 OHLC data. It requires tick or sub-minute
data (consistent with Option C below). If tick data is acquired per Option C,
Roll's estimator becomes viable. Without tick data, Amihud illiquidity
(|return|/volume) remains the only feasible liquidity proxy from existing data.

### Interaction with existing findings

| Finding | Interaction |
|---------|------------|
| DFL-06 | Analyses assume 13-field data. DFL-15 asks: is 13 fields enough? |
| DFL-09 | Scope clarification for SSE-D-02. DFL-15 is a different scope question: what data enters the pipeline, not what data enters grammar |
| DFL-10 | Stage 2.5 profiles ALL available fields. DFL-15 determines what's available |
| DFL-13 | Cross-exchange validation needs external data. DFL-15 scopes whether that's in framework |
| SSE-D-02 (018) | OHLCV-only for grammar. DFL-15 is about pipeline input, not grammar input — orthogonal |
| DFL-16 | Cross-asset context signals require external data (altcoin OHLCV, BTC dominance). DFL-15's scope decision determines whether this data enters the pipeline |

**Open questions**:
- Should the framework spec REQUIRE a minimum field set (mandating OHLCV+volume+
  taker at minimum), or be fully agnostic (profile whatever is provided)?
- If Option C (tick data), what is the storage and compute cost? Is it practical
  for the first campaign, or deferred to future campaigns?
- Should the scope decision be per-campaign (each campaign declares its data
  boundary) or framework-level (one boundary for all campaigns)?
- For non-crypto assets (equities, FX), the available data is very different
  (no taker_buy_vol, different microstructure). Does the scope decision need to
  be asset-class-aware?

---

## DFL-16: Cross-Asset Context Signals for Single-Asset Strategy

- **issue_id**: X38-DFL-16
- **classification**: Judgment call
- **opened_at**: 2026-03-31
- **opened_in_round**: 0
- **current_status**: Open

> **Debate scope note**: X20 (Cross-Asset Portfolio) tested TRADING multiple
> assets → CLOSE (BTC alpha dominates). DFL-16 addresses a fundamentally
> different question: does data FROM other assets contain information that
> IMPROVES a BTC-only strategy? This is about SIGNAL, not DIVERSIFICATION.

**Motivation**:

Every DFL-06 analysis examines BTC/USDT in isolation. Yet real crypto markets
are interconnected:

- When altcoins crash first, BTC often follows (or leads)
- When BTC dominance rises, it signals risk-off within crypto
- ETH/BTC ratio tracks crypto-specific risk appetite
- Total crypto market volume indicates sector-wide participation

The EMA(21d) regime filter works because D1 trend CONTEXT improves H4 entries.
The same logic suggests CROSS-ASSET CONTEXT might improve BTC entries — using
other assets' behavior as an information source, not as trading targets.

**Evidence from btc-spot-dev**:

X20 results actually contain relevant evidence for this question, though X20
asked a DIFFERENT question (portfolio construction):

| X20 finding | Implication for DFL-16 |
|-------------|----------------------|
| Mean ρ = 0.343 across 14 coins | Moderate correlation → some shared signal, not redundant |
| All 14 coins pass VDO screen | VDO (taker flow imbalance) is a MARKET-WIDE phenomenon, not BTC-specific |
| Altcoin median Sharpe 0.42 (< BTC 0.735) | Altcoins are noisier but may still carry leading information |
| BTC-only >> any portfolio | BTC is best to TRADE. But is it best to OBSERVE in isolation? |

**Proposal**: Investigate whether cross-asset data improves BTC strategy
performance as CONTEXT SIGNAL, not as trading targets.

### Specific signals to test

| Signal | Derivation | Hypothesis | Data needed |
|--------|-----------|-----------|-------------|
| **BTC dominance** | BTC_mcap / Total_crypto_mcap | Rising dominance = crypto risk-off → BTC relative strength → trend more reliable | Total crypto market cap (CoinGecko/CMC API, daily) |
| **Altcoin correlation spike** | Rolling 30d correlation of top-10 altcoins | High correlation = herding / systemic event → regime change signal | OHLCV for top-10 altcoins (Binance API, H4/D1) |
| **ETH/BTC ratio** | ETH price / BTC price | Ratio declining = capital rotation to BTC (quality flight) → bullish BTC signal | ETH/USDT price (single pair, easy) |
| **Cross-asset VDO consensus** | Mean VDO across top-5 coins | If taker imbalance is positive across many coins simultaneously → stronger directional conviction | Taker volume data for 5 coins (Binance API) |
| **Altcoin-leads-BTC** | Granger-causality test: altcoin returns → BTC returns | Do smaller coins react first to information, with BTC lagging? (less liquid → faster price discovery in some models) | Return series for 5-10 altcoins |

### Contamination and scope considerations

- Cross-asset signals are EXTERNAL CONTEXT, similar to D1 EMA regime filter
  being temporal context for H4 entries
- They do NOT modify the core strategy (VTREND E5) — they provide an
  additional filtering or sizing dimension
- Grammar integration: cross-asset signals are NOT OHLCV (SSE-D-02 restricted).
  They enter ONLY via human templates (DFL-03 channel 1, DFL-09 scope)
- WFO validation: any cross-asset filter must pass the same 7-gate pipeline
  as any other strategy modification
- Statistical budget (DFL-11): each cross-asset feature formally tested
  consumes 1 budget unit

### Relationship to X20

| Aspect | X20 (done) | DFL-16 (proposed) |
|--------|-----------|-------------------|
| Question | Trade multiple assets? | Use other assets' data for BTC signal? |
| Conclusion | BTC-only wins (Sh 0.735 >> portfolio 0.259) | Unknown — never tested |
| Data overlap | 14 coins OHLCV+VDO | Same coins, but as INPUTS not TARGETS |
| Mechanism | Portfolio diversification (return blending) | Context signal (information enrichment) |
| Budget cost | N/A (closed study) | 1 unit per formally validated signal |

### Interaction with existing findings

| Finding | Interaction |
|---------|------------|
| DFL-11 | Budget: each cross-asset signal formally tested consumes 1 budget unit |
| DFL-15 | Data acquisition scope: cross-asset data (altcoin OHLCV, BTC dominance) requires external data not in current CSV — DFL-15 scopes whether this is in framework |
| DFL-03 | Human templates channel 1: cross-asset signals enter via human template (NOT grammar, per SSE-D-02) |
| DFL-09 | Scope: cross-asset signals are non-OHLCV. Consistent with DFL-09 (analysis can use any data; grammar restricted to OHLCV) |
| DFL-08 | Graduation path: cross-asset features follow same 5-stage path as any other feature |
| X20 | Prior evidence: X20 WFO 1/4 for multi-coin portfolios is circumstantial evidence that cross-asset signals may be temporally unstable. DFL-16 asks a different question (context vs portfolio), but the WFO instability is a relevant prior |

### Practical consideration

This is the LOWEST PRIORITY of the 6 new findings. The expected value is
uncertain — cross-asset signals may add nothing. X20's WFO failure (1/4) is
circumstantial evidence that cross-asset relationships are temporally unstable,
though X20 tested portfolio construction (return blending), not context signals
(information enrichment). The COST of testing is low (data acquisition easy,
follows DFL-06/07 methodology). The main risk is budget consumption (DFL-11).

**Recommendation**: Defer to AFTER DFL-06 analyses exhaust intra-BTC patterns.
If budget remains, test cross-asset signals. If budget is exhausted, skip.
(This recommendation pre-disposes toward deferral — the debate may decide
otherwise.)

**Open questions**:
- Should cross-asset signals be tested within the framework's standard pipeline,
  or as a separate research study (like X20)?
- Data staleness: if using CoinGecko/CMC for BTC dominance, how often is data
  updated? Does daily resolution suffice for H4 strategy?
- If an altcoin delists or structurally changes, does the cross-asset signal
  break? How robust is a signal that depends on other assets' continuity?
- Legal/compliance: for non-crypto applications (equities, FX), cross-asset
  data may have different licensing requirements. Should the framework address
  this, or is it per-campaign configuration?

---

## DFL-17: Pipeline Validation via Synthetic Known-Signal Injection

- **issue_id**: X38-DFL-17
- **classification**: Thiếu sót
- **opened_at**: 2026-03-31
- **opened_in_round**: 0
- **current_status**: Open

> **Debate scope note**: DFL-07 §E uses synthetic data to test NULL hypotheses
> (is this pattern real?). DFL-17 uses synthetic data to test the PIPELINE
> ITSELF (can it detect a real pattern?). These are complementary: §E validates
> discoveries, DFL-17 validates the discovery machinery.

**Motivation**:

DFL-06 proposes 10 systematic analyses. DFL-07 proposes a 3-phase workflow
(SCAN → DEEP DIVE → VALIDATION). DFL-08 proposes a 5-stage graduation path.
DFL-11 proposes a two-tier screening system.

But how do we know the pipeline WORKS? If VDO-like alpha exists in data, will
the pipeline find it? What if a pattern is real but the pipeline's screening
thresholds, null models, or graduation gates filter it out?

**The problem**: The pipeline has never been validated against a KNOWN positive.
DFL-07 §E validates against known NEGATIVES (null models — data with no signal).
But there is no corresponding test against known POSITIVES (data with a planted
signal of known strength).

This is the standard engineering practice of CALIBRATION: before deploying a
measurement instrument, test it against a known reference to verify it measures
correctly.

**Proposal**: A synthetic data validation protocol for the discovery pipeline.

### Protocol 1: Known-signal injection (sensitivity)

**Goal**: Determine the MINIMUM DETECTABLE SIGNAL — the weakest genuine pattern
the pipeline can reliably find.

**Method**:

```
1. Generate base synthetic data:
   - Use DFL-07 §E2 GARCH model fitted to real BTC/USDT data
   - Preserves: volatility clustering, fat tails, serial dependence in |returns|
   - Destroys: any genuine predictive features (by construction)

2. Inject a known signal of controlled strength:
   - Create a synthetic feature X that predicts forward returns
   - Predictive strength parameter: IC = {0.01, 0.02, 0.05, 0.10, 0.15, 0.20}
   - Signal type: linear (X → return) or threshold (X > threshold → positive return)

3. Run the pipeline:
   - DFL-06 Analysis (relevant subset) → detect X?
   - DFL-07 Phase 1 SCAN → X passes screening?
   - DFL-08 Stage 1 → X becomes candidate?
   - DFL-08 Stage 2 → X passes deep dive?
   - DFL-07 Phase 3 VALIDATION → X passes WFO?

4. Measure detection rate:
   - At each IC level, run 100 synthetic datasets
   - Detection rate = fraction where pipeline detects X at each stage
   - Minimum detectable IC = lowest IC with >80% detection rate
```

**Interpretation**:
- If minimum detectable IC = 0.02 → pipeline can find weak signals (good)
- If minimum detectable IC = 0.15 → pipeline only finds strong signals (bad —
  VDO's IC is only ~0.10-0.15, and weaker-but-real signals would be missed)

### Protocol 2: No-signal false positive rate (specificity)

**Goal**: Determine how many FALSE POSITIVES the pipeline produces when NO
genuine signal exists.

**Method**:

```
1. Generate 100 synthetic datasets with ZERO signal
   (same GARCH base, no injected features)

2. Create 13 synthetic fields mimicking the CSV structure
   (correlated with returns ONLY through known GARCH properties)

3. Run the full pipeline on each dataset

4. Count false positives:
   - Features that pass DFL-08 Stage 1 (candidate)
   - Features that pass DFL-08 Stage 2 (deep dive)
   - Features that pass DFL-08 Stage 5 (validation)

5. False positive rate at each stage:
   - FPR_stage1 = mean candidates per no-signal dataset
   - FPR_stage5 = mean validated features per no-signal dataset
```

**Interpretation**:
- FPR_stage5 = 0.02 → 2% of no-signal datasets produce a false validated
  feature → acceptable
- FPR_stage5 = 0.20 → 20% → pipeline is too permissive, gates need tightening

**Relationship to DFL-07 §E**: Protocol 2 and DFL-07 §E4 both run the pipeline
on null-signal data. The difference: §E4 tests per-analysis null rejection
(1000 datasets, one analysis at a time), Protocol 2 tests END-TO-END pipeline
false positive rate (100 datasets, all stages). §E4 answers "does Analysis N
produce false discoveries?" Protocol 2 answers "does the FULL pipeline
(screening → deep dive → validation) produce false validated features?" If both
are implemented, §E4 results are per-stage inputs; Protocol 2 is the aggregate
system-level test. The smaller N (100 vs 1000) is a compute compromise — the
95% CI on FPR at N=100 spans ±7.8 percentage points, which may be insufficient
for precise calibration.

### Protocol 3: VDO reconstruction test (ecological validity)

**Goal**: Test whether the pipeline's DFL-06 ANALYSIS PATH (not grammar scan)
would have found VDO — using VDO as a KNOWN POSITIVE calibration target.

**Critical scope constraint**: VDO uses `taker_buy_base_vol`, which is NOT an
OHLCV field. The grammar (SSE-D-02) is OHLCV-only. Therefore VDO CANNOT be
found by grammar enumeration — by construction, not by pipeline failure.
Protocol 3 tests ONLY the DFL-06 analysis path (which has access to all 13
fields per DFL-09).

**Method**:

```
1. Use real BTC/USDT data
2. Compute actual VDO signal (taker_buy_ratio)
3. Verify VDO's known properties: DOF-corrected p=0.031 (Sharpe), p=0.004 (MDD)
   (Note: VDO's trade-level IC has not been formally measured — the p-values
   above are from strategy-level 16-timescale tests, not direct IC estimation.
   IC ≈ 0.10-0.15 is an ASSUMPTION that should be verified as part of Protocol 3)
4. Run the DFL-06 analysis path AS IF VDO were unknown:
   - DFL-06 Analysis 1 → would MI/IC screening rank taker_buy_ratio highly?
   - DFL-07 Phase 1 SCAN → would it pass top-N screening at N=200?
   - DFL-08 Stage 2 → would it pass deep dive + null model test?
   - DFL-11 budget → would it survive Holm correction at current K?

5. Result:
   - Pipeline finds VDO → PASS (pipeline works for known positives)
   - Pipeline misses VDO → FAIL (pipeline is filtering out real signals)
```

**This is the single most important test**: if the DFL-06 analysis path
CANNOT surface VDO as a candidate — the project's only validated alpha
source — then the analysis methodology (DFL-07) needs recalibration before
running the full DFL-06 suite. Note: a FAIL here does NOT mean "fundamental
redesign" — it means the screening thresholds or methodology need tuning,
not that the architecture is wrong. Some discoveries may inherently require
human intuition and cannot be fully systematized.

### Integration with existing findings

| Finding | Interaction |
|---------|------------|
| DFL-06 | Pipeline to be validated. Protocol 1-2 test DFL-06's ability to detect signals |
| DFL-07 §E | Complementary: §E tests discoveries against nulls, DFL-17 tests pipeline against knowns |
| DFL-08 | Graduation path stages are tested end-to-end |
| DFL-11 | Budget constraints: does the two-tier screening survive Protocol 2 (false positives)? |
| DFL-12 | Depth-2 grammar: can pipeline detect depth-2 signals (e.g., ratio features)? |
| DFL-13 | Protocol 3 uses taker_buy_base_vol — if taker classification is unreliable (DFL-13 Category A), calibration is affected |

**Open questions**:
- Should Protocol 1-3 run BEFORE or AFTER DFL-06 analyses? Before = validates
  pipeline first. After = DFL-06 results calibrate what "detectable" means
- Compute cost: 100 synthetic datasets × full pipeline = significant compute.
  Can be reduced with faster proxy pipeline (skip visualization, use summary
  statistics only)
- Protocol 3 scope RESOLVED in body: all 13 fields via DFL-06 analysis path
  (VDO uses taker_buy_base_vol which is non-OHLCV, so grammar path is
  structurally excluded — not a meaningful test target)
- If Protocol 3 fails, what is the fix? Loosen screening thresholds? Change
  methodology? Accept that some discoveries require human intuition and
  cannot be systematized?

---

## DFL-18: Systematic Feature Regime-Conditional Profiling

- **issue_id**: X38-DFL-18
- **classification**: Thiếu sót
- **opened_at**: 2026-03-31
- **opened_in_round**: 0
- **current_status**: Open

> **Debate scope note**: DFL-06 analyses test features individually. DFL-14
> classifies features by shelf-life. DFL-18 bridges the gap: a systematic
> protocol for testing EVERY discovered feature across EVERY identified regime,
> producing a feature × regime interaction matrix. This is a quality assurance
> layer for the discovery pipeline.

**Motivation**:

E5-ema21D1 works because its components are regime-INVARIANT:
- EMA crossover: p=0.0003, survives Bonferroni (all regimes)
- VDO filter: 16/16 timescales (not regime-conditional)
- EMA(21d) regime: 16/16 ALL metrics (works in both bull and bear)

This invariance was verified AD HOC during development — each component was
tested across conditions by human judgment. But the framework has no
SYSTEMATIC protocol for verifying regime-invariance of newly discovered
features.

**The risk**: DFL-06 analyses may discover a feature with strong full-sample
statistics (high MI, significant IC, passes null model) that only works in
bull markets. If the graduation path (DFL-08) doesn't catch this, the feature
enters production and fails during the next bear market.

**Evidence**: X11 (short-side) found BTC shorts are negative-EV at ALL
timescales. This was discovered by testing across regime — the full-sample
statistics looked plausible, but regime decomposition revealed the signal
was entirely regime-dependent. Without regime testing, X11 would have
appeared viable.

**Proposal**: A systematic regime-conditional profiling protocol that runs as
part of DFL-08 Stage 2 (deep dive) for every feature candidate.

### Regime definitions

Two types of regimes, both applied to every feature candidate:

**Type 1: Market regimes** (exogenous — determined by price action):

| Regime | Definition | Periods in BTC data |
|--------|-----------|---------------------|
| Bull trend | D1 close > EMA(21d) AND 60d return > 0 | 2017Q4, 2019Q2-Q3, 2020Q4-2021Q2, 2021Q4, 2023Q4-2024Q1 |
| Bear trend | D1 close < EMA(21d) AND 60d return < 0 | 2018, 2019Q4, 2022Q2-Q4 |
| Range/chop | 60d return ≈ 0 (within ±10%) | 2019Q1, 2020Q1-Q3, 2023Q1-Q3 |
| High volatility | Rolling 30d realized vol > 75th percentile | 2017Q4-2018Q1, 2020Q3, 2021Q2, 2022Q2 |
| Low volatility | Rolling 30d realized vol < 25th percentile | 2019Q2-Q4, 2023Q2-Q3, 2025Q1 |

**Type 2: Volume regimes** (endogenous — determined by market participation):

| Regime | Definition | Periods in BTC data |
|--------|-----------|---------------------|
| High volume | Rolling 30d volume > 75th percentile | 2017Q4-2018Q1, 2021Q1-Q2 |
| Low volume | Rolling 30d volume < 25th percentile | 2019Q2-Q4, 2024Q4-2025Q1 |
| High num_trades (optional) | Rolling 30d num_trades > 75th percentile | May differ from high volume (many small trades vs few large). Include only if DFL-13 validates num_trades trustworthiness |

### Profiling protocol

For every feature candidate F at DFL-08 Stage 2:

```
1. Compute F's IC (Spearman rank correlation with forward returns)
   for EACH regime defined above

2. Build the interaction matrix:

   Feature F    | Bull | Bear | Range | Hi-Vol | Lo-Vol | Hi-Volume | Lo-Volume
   -------------|------|------|-------|--------|--------|-----------|----------
   IC           | 0.12 | 0.08 | -0.01 | 0.15  | 0.03   | 0.11     | 0.04
   p-value      | 0.01 | 0.03 | 0.82  | 0.005 | 0.45   | 0.02     | 0.31
   N (trades)   | 45   | 52   | 91    | 47     | 47     | 47       | 47

3. Guard: require min N per regime cell ≥ 25 trades. If any cell has
   N < 25, mark that cell as INSUFFICIENT — do not compute IC for it.
   Stability score computed only over cells with sufficient N.

4. Guard: require max(|IC_regime|) > 0.03 (minimum signal threshold).
   If all |IC| < 0.03, the feature is NOISE — classify directly as
   NO_SIGNAL without computing stability score. This prevents noise
   features from scoring S ≈ 1.0 and passing as "invariant."

5. Compute regime-stability score (only for features that pass guards):
   S = min(IC_regime) / max(IC_regime)
   where min and max are over regime cells with sufficient N.

   Interpretation:
   - S ≈ 1.0 AND max(IC) > 0 → regime-invariant (ideal, like VDO)
   - 0 < S ≤ 0.5 → regime-dependent (feature works in some regimes)
   - S ≤ 0 → regime-adversarial (feature hurts in some regimes)
   - max(IC) ≤ 0 → UNIVERSALLY_HARMFUL (reject regardless of S value —
     the min/max formula produces S > 1 when all ICs are negative, and
     division by zero when max(IC) = 0, both degenerate cases)

6. Classification:
   - NO_SIGNAL (guard 4): all |IC| < 0.03 → discard
   - UNIVERSALLY_HARMFUL: max(IC) ≤ 0 → reject
   - REGIME-INVARIANT: S > 0.5 AND max(IC) > 0.03 → proceed
   - REGIME-DEPENDENT: 0 < S ≤ 0.5 → flag in DFL-02 report, warn human
   - REGIME-ADVERSARIAL: S ≤ 0 → strong warning, human must justify
```

**Regime overlap handling**: The 8 regimes (5 market + 3 volume) can co-occur
(a bar can be both "bull trend" AND "high volatility"). The protocol computes
IC per regime INDEPENDENTLY — the same trades contribute to multiple cells.
This means ICs are NOT orthogonal. The stability score reveals whether a
feature's IC changes across conditions, but cannot identify the CAUSAL driver
when conditions overlap (e.g., high IC in "bull" and "high-vol" may both be
driven by volatility if bull periods coincide with high vol). The interaction
matrix should be interpreted as a SCREENING tool, not a causal analysis.
Disentangling overlapping regimes requires multivariate analysis (outside this
protocol's scope).

### Integration with DFL-08 graduation path

| DFL-08 Stage | DFL-18 addition |
|-------------|-----------------|
| Stage 1 (candidate) | No change — screening is unconditional |
| Stage 2 (deep dive) | **ADD: regime-conditional profiling** (this finding). Interaction matrix and stability score computed. Report includes regime breakdown |
| Stage 3 (human decision) | Human sees stability score. REGIME-DEPENDENT features require explicit human justification |
| Stage 4 (registry) | `regime_stability_score` added to registry metadata |
| Stage 5 (validation) | No change — WFO already provides time-series robustness |

### Relationship to DFL-14 shelf-life

DFL-14 and DFL-18 both classify features by regime behavior, but using
DIFFERENT methods and regime definitions:

| Aspect | DFL-14 Layer 3 | DFL-18 |
|--------|---------------|--------|
| Regime source | Layer 2 DGP-detected (PELT/CUSUM) | Hand-defined (bull/bear/range/vol quartiles) |
| Test statistic | KS p < 0.05 across DGP regimes | Stability score S = min(IC)/max(IC) |
| Classification | STRUCTURAL / REGIME-DEPENDENT / EPOCH-SPECIFIC | NO_SIGNAL / REGIME-INVARIANT / REGIME-DEPENDENT / REGIME-ADVERSARIAL / UNIVERSALLY_HARMFUL |
| Applied at | DFL-08 Stage 2 | DFL-08 Stage 2 |

The two can produce CONFLICTING classifications (e.g., DFL-14 says STRUCTURAL
because feature passes across DGP regimes, but DFL-18 says REGIME-DEPENDENT
because IC differs between bull and bear). When they conflict:
- Both classifications are recorded as metadata
- Human researcher (Tier 3 authority) decides which is more relevant
- DGP-detected regimes (DFL-14) are more principled but may miss regimes
  that DGP detection doesn't identify; hand-defined regimes (DFL-18) are
  more intuitive but subject to hindsight bias in regime definition

### Relationship to DFL-06 conditional analyses

DFL-06 Analysis 9 (conditional/event-based dynamics) studies MARKET EVENTS.
DFL-18 studies FEATURE BEHAVIOR across regimes. The distinction:

| Aspect | DFL-06 Analysis 9 | DFL-18 |
|--------|-------------------|--------|
| Question | What happens AFTER events? | Does feature F work IN ALL regimes? |
| Subject | Market dynamics | Feature-return relationship |
| When applied | During raw data exploration | After feature discovered, during graduation |
| Output | Event study plots, post-event return distributions | Feature × regime interaction matrix, stability score |

### Interaction with existing findings

| Finding | Interaction |
|---------|------------|
| DFL-08 | Stage 2 extended with regime-conditional profiling (mandatory) |
| DFL-14 | Complementary classification — different regime sources and test statistics. Resolution protocol needed when they conflict |
| DFL-06 Analysis 9 | Related but different scope (market events vs feature behavior). Timing distinction: 9 during exploration, 18 during graduation |
| DFL-07 A5 | HMM-detected regimes could replace hand-defined regimes (open question) |
| DFL-11 | Low-N regime cells reduce effective power per feature — may affect budget consumption |
| DFL-13 | Volume regime definitions (Type 2) use rolling volume. If volume is unreliable (DFL-13 Category A), regime boundaries are affected |

### Open questions

- Regime definitions: are the 7 core regimes (+ 1 optional) sufficient? Should
  HMM-detected regimes (DFL-07 A5) replace hand-defined regimes?
- Minimum N per regime: protocol now guards N ≥ 25, but with 188 trades split
  across 7+ regimes, many cells may be INSUFFICIENT. Should the number of
  regimes be reduced to ensure sufficient N per cell?
- Stability score formula: `min/max` is simple but sensitive to outliers.
  Alternative: coefficient of variation of IC across regimes. Which is more
  informative?
- Should regime-conditioning be applied to EXISTING features (VDO, EMA regime)
  retroactively as validation? Or only to newly discovered features?
- Interaction with WFO: WFO already tests time-series robustness. Does
  regime-conditional profiling add independent information, or is it redundant
  with WFO (which implicitly tests across regimes by testing across time)?

---

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 018 | SSE-D-02 (rule 1) | Bounded ideation results-blind vs discovery loop results-aware | DFL-04 defines contamination boundary; DFL-03 proposes deliberate exception for human templates |
| 018 | SSE-D-02 (rule 3) | OHLCV-only rule vs DFL-06 scan using all 13 fields — analysis ≠ ideation | DFL-09 proposes scope clarification: SSE-D-02 applies to automated ideation only, not to analysis or human templates |
| 018 | SSE-D-02 (rule 3) | OHLCV-only rule vs depth-2 composition operators — do new operators change scope? | DFL-12 proposes composition operators within OHLCV-only grammar; DFL-09 scope applies |
| 018 | SSE-D-11 | APE v1 no code gen. DFL-05 proposes deliberation-gated code authoring as SEPARATE mechanism | DFL-05 defines scope boundary: automated gen (SSE-D-11) vs deliberation-gated authoring (DFL-05) |
| 017 | ESP-01 | epistemic_delta.json vs DiscoveryReport — complementary scope | DFL-02 defines complementary (not competing) reporting |
| 017 | ESP-04 | Budget governor vs human "investigate this" directives | DFL-03 feedback = input to human decisions, not budget override |
| 002 | F-04 | Firewall typed schema — analysis outputs need classification | DFL-04 classifies all analysis outputs as process observations |
| 003 | F-05 | Pipeline stages — **DFL-10 proposes Stage 2.5** between Stages 2-3 | 003 owns pipeline stage count. DFL-10 proposes; 003 decides |
| 006 | F-08 | Feature registry acceptance — DFL-08 Stage 4 + DFL-11 budget metadata | DFL-08 defines interface; DFL-11 proposes budget_spent field; F-08 (006) defines registry schema |
| 013 | SSE-09 (Holm) | Grammar scan correction vs discovery loop budget — separate pools? | DFL-11 defines discovery-specific budget; 013 owns grammar-scan correction |
| 015 | F-14 | DFL-10 proposes `data_profile.json` as new artifact | 015 owns artifact enumeration; DFL-10 proposes; 003 mediates |
| 009 | F-10 | Data integrity audit scope — DFL-13 proposes trustworthiness layer BELOW integrity | DFL-13 validates data accuracy, F-10 validates data completeness. Complementary, not competing |
| 003 | F-05 | Pipeline stages — **DFL-10 Stage 2.5** + **DFL-13 trustworthiness** + **DFL-15 data scope** | 003 owns pipeline stage design. DFL-10/13/15 propose; 003 decides staging |
| 013 | SSE-04 (convergence thresholds) | DGP breaks across campaigns — DFL-14 shelf-life classification | DFL-14 regime/epoch classification feeds into 013's convergence framework (equivalence thresholds may need DGP-conditioning) |
| 018 | SSE-D-02 (rule 3) | OHLCV-only grammar vs cross-asset context signals (DFL-16) | DFL-16 signals enter via human templates only (DFL-03 channel 1), not grammar. Consistent with DFL-09 |

---

## Decision summary — what debate must resolve

Debate for Topic 019 must produce decisions on these questions, grouped by
dependency (earlier decisions constrain later ones):

**Tier 1 — Foundational (resolve first)**:

| ID | Decision | Finding | Alternatives |
|----|----------|---------|-------------|
| D-01 | Is DFL-06/07 analysis a DIFFERENT activity from SSE-D-02 ideation? | DFL-09 | YES (analysis exempt from OHLCV-only) / NO (analysis also restricted) |
| D-02 | Is human-mediated feedback "contamination laundering" or fundamentally different from automated feedback? | DFL-04 | Different (process observations) / Same (contamination) |
| D-03 | Is deliberation-gated code authoring a SEPARATE mechanism from APE (SSE-D-11) or an exception? | DFL-05 | Separate (both exist) / Exception (requires v2+ gate) |

**Tier 2 — Mechanisms (after Tier 1)**:

| ID | Decision | Finding | Alternatives |
|----|----------|---------|-------------|
| D-04 | Should grammar support depth-2 composition operators in v2? | DFL-12 | YES (expand grammar) / NO (human templates only for composition) |
| D-05 | Should the pre-filter use top-N ranking or p-value threshold? | DFL-08+DFL-11 | Top-N (fixed, declared) / P-value (data-dependent) / Hybrid |
| D-06 | Is the human SSE-D-02 exception for templates correct? | DFL-03 | YES (provenance-tracked) / NO (results-blind required for ALL sources) |
| D-07 | Stage 2.5 as new stage or expand Stage 2? | DFL-10 | New Stage 2.5 / Expand Stage 2 / Reject (not needed) |
| D-08 | AI analysis layer: automatic or on-demand? | DFL-01 | Automatic (post-validation) / On-demand (human request) / Both |
| D-13 | AI analysis layer: stateless or stateful (memory across reports)? | DFL-01 | Stateless / Stateful (contamination risk per DFL-04) |
| D-14 | Findings cap per report? | DFL-02 | Fixed N=10 / Dynamic by confidence / Uncapped |

**Tier 3 — Budget & governance (after Tier 2)**:

| ID | Decision | Finding | Alternatives |
|----|----------|---------|-------------|
| D-09 | Separate budget for discovery vs grammar scan? | DFL-11 | Separate (disjoint families) / Pooled (single FWER) |
| D-10 | Retroactive counting of pre-framework tests? | DFL-11 | Clean start (k=0) / Full accounting / Partial (selected) |
| D-11 | How to handle Tier 0 selection bias? | DFL-11 | Permutation calibration / Conservative factor / Simulation study first |
| D-12 | DFL-06/07 scope: architecture or research plan? | DFL-06+07 | Architecture (method space) / Research plan (defer to campaign) / Split |

**Tier 4 — Data foundation & quality assurance (independent of Tier 1-3)**:

| ID | Decision | Finding | Alternatives |
|----|----------|---------|-------------|
| D-15 | Should data trustworthiness be a framework stage? | DFL-13 | Stage 1.5 (before audit) / Part of Stage 2 / One-time validation |
| D-16 | Cross-exchange data: acquire for validation or document as assumption? | DFL-13 | Acquire (one-time) / Skip (accept risk) |
| D-17 | Feature shelf-life classification: mandatory in graduation path? | DFL-14 | Mandatory (DFL-08 Stage 2 addition) / Advisory (human judgment) / Not needed (WFO sufficient) |
| D-18 | Data acquisition scope: framework-level or per-campaign? | DFL-15 | Framework-level minimum set / Per-campaign declaration / Data-agnostic (accept whatever) |
| D-19 | Cross-asset context: in-scope for first campaign or deferred? | DFL-16 | After DFL-06 exhausts intra-BTC / In parallel / Out of scope for v1 |
| D-20 | Pipeline validation via synthetic data: before or after DFL-06? | DFL-17 | Before (validate pipeline first) / After (calibrate from real results) / In parallel |
| D-21 | Regime-conditional profiling: mandatory or optional in graduation? | DFL-18 | Mandatory (all features) / Optional (human judgment) / Only for flagged features |

---

## Summary table

| Issue ID | Finding | Classification | Status |
|----------|---------|---------------|--------|
| X38-DFL-01 | AI result analysis & pattern surfacing | Thiếu sót | Open |
| X38-DFL-02 | Human-facing report contract | Thiếu sót | Open |
| X38-DFL-03 | Human feedback capture & grammar evolution | Judgment call | Open |
| X38-DFL-04 | Contamination boundary for the discovery loop | Thiếu sót | Open |
| X38-DFL-05 | Deliberation-gated code authoring | Judgment call | Open |
| X38-DFL-06 | Systematic raw data exploration (10 analyses) | Thiếu sót | Open |
| X38-DFL-07 | Raw data analysis methodology (6 categories) | Thiếu sót | Open |
| X38-DFL-08 | Feature candidate graduation path (5 stages) | Thiếu sót | Open |
| X38-DFL-09 | SSE-D-02 scope clarification for systematic scan | Thiếu sót | Open |
| X38-DFL-10 | Pipeline integration: Stage 2.5 data characterization | Thiếu sót | Open |
| X38-DFL-11 | Statistical budget accounting (two-tier screening) | Thiếu sót | Open |
| X38-DFL-12 | Grammar depth-2 composition (search space expansion) | Thiếu sót | Open |
| X38-DFL-13 | Data trustworthiness & cross-source validation | Thiếu sót | Open |
| X38-DFL-14 | Non-stationarity protocol — DGP change detection & feature shelf-life | Thiếu sót | Open |
| X38-DFL-15 | Resolution gap assessment & data acquisition scope decision | Judgment call | Open |
| X38-DFL-16 | Cross-asset context signals for single-asset strategy | Judgment call | Open |
| X38-DFL-17 | Pipeline validation via synthetic known-signal injection | Thiếu sót | Open |
| X38-DFL-18 | Systematic feature regime-conditional profiling | Thiếu sót | Open |
