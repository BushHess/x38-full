# Findings Under Review — Regime Dynamics

**Topic ID**: X38-T-19F
**Opened**: 2026-04-02
**Author**: human researcher

2 findings about how data changes over time and whether features are stable
across regimes. Split from Topic 019 (DFL-14 originally in 019E, DFL-18
originally in 019F). Regrouped 2026-04-02 to resolve the DFL-14/DFL-18
cross-boundary tension: these two findings have a documented conflict (DGP-
detected regimes vs hand-defined regimes producing different classifications)
that debaters can now resolve directly within a single topic.

Theme: "How does data change over time? Are features stable across regimes?"

These are Tier 4 decisions, INDEPENDENT of the discovery loop architecture
(Tier 1-3). Can be debated in PARALLEL with all other 019 sub-topics.

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

## DFL-14: Non-Stationarity Protocol — DGP Change Detection & Feature Shelf-Life

- **issue_id**: X38-DFL-14
- **classification**: Thieu sot
- **opened_at**: 2026-03-31
- **opened_in_round**: 0
- **current_status**: Open

> **Debate scope note**: DFL-06 Analysis 7 + DFL-07 A5 already provide detection
> TOOLS (PELT, CUSUM, rolling metrics) for non-stationarity — including structural
> breaks. DFL-14 provides the RESPONSE PROTOCOL: how to interpret detected breaks,
> what framework-level actions follow, and how to classify features by prospective
> validity. DFL-14's value is governance (what to DO), not method (how to DETECT).

**Motivation**:

BTC/USDT 2017-08 -> 2026-02 spans multiple market microstructure regimes:

| Period | Market characteristic | Data implication |
|--------|---------------------|------------------|
| 2017-2018 | Retail-dominated, high volatility, ICO era | High volume, high num_trades, extreme taker imbalance |
| 2019-early 2020 | Post-crash, low volatility, consolidation | Low volume, compressed spreads, fewer trades |
| mid-2020-2021 | DeFi Summer (mid-2020), institutional entry (MicroStrategy Aug 2020, Tesla Feb 2021), bull market | Volume surge, changed participant composition, DeFi cross-venue flows |
| 2021-2022 | Peak -> crash, Terra/Luna, FTX collapse | Extreme events, structural breaks in correlations |
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
| Regime shift | Cyclical, recurring, bounded | Bull -> bear cycle | Feature may return. Design for regime-conditioning |

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

### Layer 2 -> Layer 3 handoff

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
| **EPOCH-SPECIFIC** | Feature exists only in a specific historical period | Structural break in feature-return relationship. Post-break IC ~ 0. No regime where feature works post-break | Short shelf-life. WARN: may not exist in future data |

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

### Interaction with existing findings

| Finding | Interaction |
|---------|------------|
| DFL-06 Analysis 7 | Analysis 7 + DFL-07 A5 provide detection TOOLS (PELT, CUSUM, rolling metrics). DFL-14 provides the RESPONSE protocol (classification, actions) |
| DFL-07 A5 | Change detection methods applied to DGP-level relationships (Layer 2), not just strategy-level signals |
| DFL-08 Stage 2 | Shelf-life classification extends Stage 2's existing "structural break detection" gate with named classes and DFL-02 integration |
| DFL-10 Stage 2.5 | `data_profile.json` could include DGP regime count as a field |
| DFL-11 | Epoch-specific features: should they consume budget if shelf-life is short? |
| DFL-13 | If data fields are unreliable (Category A), Layer 2 DGP detection on those fields is compromised |
| DFL-18 | **KEY TENSION — see below**. Complementary regime profiling. DFL-14 = DGP-detected regimes + classification. DFL-18 = hand-defined regimes + stability score. May produce different answers — resolution is a primary debate point for this topic |
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

## DFL-18: Systematic Feature Regime-Conditional Profiling

- **issue_id**: X38-DFL-18
- **classification**: Thieu sot
- **opened_at**: 2026-03-31
- **opened_in_round**: 0
- **current_status**: Open

> **Debate scope note**: DFL-06 analyses test features individually. DFL-14
> classifies features by shelf-life. DFL-18 bridges the gap: a systematic
> protocol for testing EVERY discovered feature across EVERY identified regime,
> producing a feature x regime interaction matrix. This is a quality assurance
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
| Range/chop | 60d return ~ 0 (within +/-10%) | 2019Q1, 2020Q1-Q3, 2023Q1-Q3 |
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

3. Guard: require min N per regime cell >= 25 trades. If any cell has
   N < 25, mark that cell as INSUFFICIENT — do not compute IC for it.
   Stability score computed only over cells with sufficient N.

4. Guard: require max(|IC_regime|) > 0.03 (minimum signal threshold).
   If all |IC| < 0.03, the feature is NOISE — classify directly as
   NO_SIGNAL without computing stability score. This prevents noise
   features from scoring S ~ 1.0 and passing as "invariant."

5. Compute regime-stability score (only for features that pass guards):
   S = min(IC_regime) / max(IC_regime)
   where min and max are over regime cells with sufficient N.

   Interpretation:
   - S ~ 1.0 AND max(IC) > 0 -> regime-invariant (ideal, like VDO)
   - 0 < S <= 0.5 -> regime-dependent (feature works in some regimes)
   - S <= 0 -> regime-adversarial (feature hurts in some regimes)
   - max(IC) <= 0 -> UNIVERSALLY_HARMFUL (reject regardless of S value —
     the min/max formula produces S > 1 when all ICs are negative, and
     division by zero when max(IC) = 0, both degenerate cases)

6. Classification:
   - NO_SIGNAL (guard 4): all |IC| < 0.03 -> discard
   - UNIVERSALLY_HARMFUL: max(IC) <= 0 -> reject
   - REGIME-INVARIANT: S > 0.5 AND max(IC) > 0.03 -> proceed
   - REGIME-DEPENDENT: 0 < S <= 0.5 -> flag in DFL-02 report, warn human
   - REGIME-ADVERSARIAL: S <= 0 -> strong warning, human must justify
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

### Relationship to DFL-06 conditional analyses

DFL-06 Analysis 9 (conditional/event-based dynamics) studies MARKET EVENTS.
DFL-18 studies FEATURE BEHAVIOR across regimes. The distinction:

| Aspect | DFL-06 Analysis 9 | DFL-18 |
|--------|-------------------|--------|
| Question | What happens AFTER events? | Does feature F work IN ALL regimes? |
| Subject | Market dynamics | Feature-return relationship |
| When applied | During raw data exploration | After feature discovered, during graduation |
| Output | Event study plots, post-event return distributions | Feature x regime interaction matrix, stability score |

### Interaction with existing findings

| Finding | Interaction |
|---------|------------|
| DFL-08 | Stage 2 extended with regime-conditional profiling (mandatory) |
| DFL-14 | **KEY TENSION — see below**. Complementary classification — different regime sources and test statistics. Resolution protocol needed when they conflict |
| DFL-06 Analysis 9 | Related but different scope (market events vs feature behavior). Timing distinction: 9 during exploration, 18 during graduation |
| DFL-07 A5 | HMM-detected regimes could replace hand-defined regimes (open question) |
| DFL-11 | Low-N regime cells reduce effective power per feature — may affect budget consumption |
| DFL-13 | Volume regime definitions (Type 2) use rolling volume. If volume is unreliable (DFL-13 Category A), regime boundaries are affected |

### Open questions

- Regime definitions: are the 7 core regimes (+ 1 optional) sufficient? Should
  HMM-detected regimes (DFL-07 A5) replace hand-defined regimes?
- Minimum N per regime: protocol now guards N >= 25, but with 188 trades split
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

## DFL-14 / DFL-18 Cross-Boundary Tension — Key Debate Point

DFL-14 and DFL-18 both classify features by regime behavior, but using
DIFFERENT methods and regime definitions. This tension was the reason for
regrouping these findings into a single topic:

| Aspect | DFL-14 Layer 3 | DFL-18 |
|--------|---------------|--------|
| Regime source | Layer 2 DGP-detected (PELT/CUSUM) | Hand-defined (bull/bear/range/vol quartiles) |
| Test statistic | KS p < 0.05 across DGP regimes | Stability score S = min(IC)/max(IC) |
| Classification | STRUCTURAL / REGIME-DEPENDENT / EPOCH-SPECIFIC | NO_SIGNAL / REGIME-INVARIANT / REGIME-DEPENDENT / REGIME-ADVERSARIAL / UNIVERSALLY_HARMFUL |
| Applied at | DFL-08 Stage 2 | DFL-08 Stage 2 |

**The conflict**: The two can produce CONFLICTING classifications. Example:
DFL-14 says STRUCTURAL because a feature passes across DGP-detected regimes,
but DFL-18 says REGIME-DEPENDENT because IC differs between bull and bear.
This happens when DGP change-point detection does not align with market-
regime boundaries (DGP breaks at structural events like FTX collapse; market
regimes cycle between bull/bear/range continuously).

**Debate must resolve**:

1. **Precedence**: When DFL-14 and DFL-18 conflict, which classification takes
   precedence? Options:
   - DGP-detected (DFL-14) always wins (more principled, data-driven boundaries)
   - Hand-defined (DFL-18) always wins (more intuitive, aligned with how
     strategies are designed)
   - Both recorded as metadata, human researcher (Tier 3) decides per feature
   - Unified regime source: use DGP-detected regimes AS INPUT to DFL-18's
     profiling protocol (eliminates the conflict by construction)

2. **Integration**: Should DFL-14 Layer 3 and DFL-18 be separate stages in
   DFL-08, or merged into a single regime assessment step?

3. **Regime source unification**: Could DFL-14's Layer 2 DGP-detected regimes
   REPLACE DFL-18's hand-defined regimes? This would eliminate the conflict
   but loses the intuitive market-regime categories (bull/bear/range) that
   align with how strategies are actually designed and evaluated.

---

## Cross-topic tensions relevant to 019F

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 013 | SSE-04 (convergence thresholds) | DGP breaks across campaigns — DFL-14 shelf-life classification | DFL-14 regime/epoch classification feeds into 013's convergence framework (equivalence thresholds may need DGP-conditioning) |
| 019E | DFL-13 (data trustworthiness) | Volume reliability affects both DFL-14 Layer 2 detection and DFL-18 volume regimes | If DFL-13 finds volume unreliable, both regime methods are compromised. 019E validation should precede or run in parallel |
| 019G | DFL-15 (data scope) | DFL-14 Layer 2 detection quality depends on available data resolution | Higher-resolution data (019G scope decision) improves DGP detection power |

---

## Decision summary — what debate must resolve

Debate for Topic 019F must produce decisions on these 2 questions, PLUS resolve
the DFL-14/DFL-18 tension. All are Tier 4 — independent of discovery loop
architecture (Tier 1-3). Can resolve in any order.

**Tier 4 — Regime dynamics (independent)**:

| ID | Decision | Finding | Alternatives |
|----|----------|---------|-------------|
| D-17 | Feature shelf-life classification: mandatory in graduation path? | DFL-14 | Mandatory (DFL-08 Stage 2 addition) / Advisory (human judgment) / Not needed (WFO sufficient) |
| D-21 | Regime-conditional profiling: mandatory or optional in graduation? | DFL-18 | Mandatory (all features) / Optional (human judgment) / Only for flagged features |

**Additional resolution required**: DFL-14/DFL-18 regime conflict (see section above).

---

## Summary table

| Issue ID | Finding | Classification | Status |
|----------|---------|---------------|--------|
| X38-DFL-14 | Non-stationarity protocol — DGP change detection & feature shelf-life | Thieu sot | Open |
| X38-DFL-18 | Systematic feature regime-conditional profiling | Thieu sot | Open |
