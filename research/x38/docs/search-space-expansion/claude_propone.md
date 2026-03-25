# Proposal: Algorithm Discovery Mechanism for Alpha-Lab Framework

**Author**: claude_code (Claude Opus 4.6)
**Date**: 2026-03-25
**Status**: Proposal — input for debate, not authoritative
**Scope**: Addresses structural gap in x38: no mechanism for search space expansion
or emergent discovery

---

## 0. Executive Summary

x38 designs an excellent **verification machine** (exhaustive scan over declared
search space, contamination firewall, protocol enforcement). But it lacks a
**discovery machine** — no mechanism creates novel features or strategy
architectures that aren't already declared.

The VDO story illustrates the gap: VDO was discovered accidentally via an AI
prompt. If VDO hadn't been declared in the Feature Engine registry, the most
perfect pipeline would never have found it. **Exhaustive scan over the wrong
space = exhaustive waste.**

This proposal adds two layers:
- **Tier 1 (Exploration)**: Mechanisms to systematically expand search space —
  creating conditions for "happy accidents"
- **Tier 2 (Recognition)**: Mechanisms to detect, validate, and catalog
  unexpected results that emerge during pipeline execution

---

## 1. Current State Analysis: Why x38 Cannot Find VDO

### 1.1 What x38 does well

| Component | Capability |
|-----------|------------|
| Protocol Engine (F-05) | 8-stage pipeline, phase gating, freeze checkpoints |
| Feature Engine (F-08) | Registry pattern, exhaustive enumeration of declared features |
| ESP (Topic 017) | Coverage tracking, cell-elite archive, budget governor |
| Contamination Firewall (Topic 002) | Typed schema, whitelist categories, shadow-only priors |
| Campaign Model (Topic 001) | Session independence, meta-knowledge handoff |

### 1.2 What x38 assumes but does not provide

The pipeline assumes a **pre-populated Feature Engine registry**. Someone must
write:

```python
@feature("vdo", family="flow", timeframe="H4",
         lookbacks=[20, 40, 60], tails=["high"])
def compute_vdo(close, volume, lookback):
    ...
```

...before the pipeline can evaluate VDO. **Who writes this function? When?
How?** x38 has no answer.

### 1.3 The three phases of algorithm discovery

```
Phase A: EXPANSION — generate novel features/architectures (MISSING in x38)
Phase B: EXECUTION — scan declared space exhaustively (Protocol Engine, 8 stages)
Phase C: LEARNING — record what was found/missed (ESP, partially covered)
```

x38 designs Phase B thoroughly and Phase C partially (via Topic 017). **Phase A
is entirely absent.**

---

## 2. Tier 1: Exploration Mechanisms

Four complementary mechanisms, each addressing a different source of novelty.

### 2.1 Generative Feature Synthesis (GFS)

**Purpose**: Automatically generate novel features by combining primitives with
operators, expanding the Feature Engine registry beyond human-declared features.

**Input**:
- Primitives from data: `close`, `high`, `low`, `volume`, `open` per timeframe
- Operator library:

| Category | Operators |
|----------|-----------|
| Transform | `log_return`, `diff`, `pct_change`, `cumsum` |
| Rolling | `rolling_mean`, `rolling_std`, `ema`, `rolling_min`, `rolling_max` |
| Normalize | `zscore`, `percentile_rank`, `min_max_scale` |
| Compare | `ratio`, `spread`, `cross_above`, `cross_below` |
| Cross-TF | `d1_to_h4_align`, `higher_tf_value` |
| Combine | `multiply`, `divide`, `subtract`, `conditional` |

- Grammar rules:
  - Max nesting depth: 3 (e.g., `ema(zscore(volume × log_return), 20)`)
  - Lookback range: [5, 200] for H4, [5, 60] for D1
  - Output must be scalar per bar (no multi-output)

**Process**:
```
Step 1: Enumerate grammar-bounded combinations
        (depth 1 → depth 2 → depth 3, progressive)
Step 2: Filter
        - Remove NaN-heavy (>20% NaN in evaluation window)
        - Remove near-constant (std < 1e-10)
        - Remove duplicates (Pearson |r| > 0.95 with existing feature)
Step 3: Tag descriptors (ESP-01 compatible)
        - mechanism: trend / volatility / flow / structure / cross_tf / composite
        - complexity: primitive (depth 1) / compound (depth 2) / complex (depth 3)
        - turnover: estimated signal flip frequency
        - origin: "GFS_auto" + grammar expression string
Step 4: Register into Feature Engine
        - Auto-generate @feature decorated functions
        - Each gets unique feature_id with "gfs_" prefix
```

**Output**:
- Extended Feature Engine registry (potentially thousands of new features)
- `gfs_manifest.json`: all generated features, their grammar expressions,
  descriptor tags, and dedup results
- `gfs_coverage_map.json`: which primitive × operator × depth combinations
  were explored

**Scale management**:
- Depth 1 (primitive × single operator × lookback): ~500-2,000 features
- Depth 2 (above × second operator): ~10,000-50,000 features
- Depth 3: ~100,000+ features (only if depth 1-2 yield no IRC)
- Progressive deepening: start depth 1 per campaign. Add depth 2 in next
  campaign only if NO_ROBUST_IMPROVEMENT. This aligns with ESP-04 budget
  governor.

**Integration with x38**:
- Runs as **Stage 2.5** (after data audit, before feature scan)
- Or runs in **Phase A** before Protocol Engine starts
- Feature Engine (F-08) needs minor extension: accept auto-generated features
  alongside hand-written ones. Same registry, same @feature contract.
- ESP-01 coverage map naturally tracks GFS-generated features
- ESP-04 budget governor applies: GFS features get same coverage floor as
  human-declared features

**Why VDO would be found**: VDO is essentially
`rolling_mean(volume × sign(close_diff), lookback)` — a depth-2 composition
that GFS grammar covers: `rolling_mean(multiply(volume, sign(diff(close))))`.

---

### 2.2 Architecture Perturbation Engine (APE)

**Purpose**: Generate novel strategy variants by applying structured mutations
to existing strategy templates.

**Input**:
- Strategy template library (initially seeded from btc-spot-dev strategies):
  - VTREND E0: EMA crossover entry + ATR trailing stop exit
  - VTREND E5: E0 + VDO filter
  - E0_ema21D1: E0 + D1 EMA regime filter
  - (extensible: any Strategy ABC implementation)
- Mutation operator catalog:

| Mutation type | Description | Example |
|---------------|-------------|---------|
| `ENTRY_SWAP` | Replace entry signal mechanism | EMA cross → momentum threshold |
| `EXIT_SWAP` | Replace exit mechanism | ATR trail → percentage trail, time stop |
| `FILTER_ADD` | Inject pre-entry filter | + volatility regime, + volume filter |
| `FILTER_REMOVE` | Remove existing filter | - VDO filter (ablation) |
| `PARAM_WIDEN` | Expand parameter search range | slow_period: [60,144] → [20,200] |
| `COMPOSE_AND` | AND-combine entries from 2 templates | entry1 AND entry2 |
| `COMPOSE_OR` | OR-combine entries from 2 templates | entry1 OR entry2 |
| `SIMPLIFY` | Remove one component entirely | E5 → E0 (remove VDO) |
| `SYMMETRIZE` | Add short-side equivalent | long-only → long/short |

- Mutation budget: 1-3 mutations per variant (complexity cap)

**Process**:
```
Step 1: Select base template
Step 2: Apply 1-3 mutations (randomly sampled or systematic sweep)
Step 3: Generate strategy.py code
        - Must implement Strategy ABC (v10 compatible)
        - Must pass smoke test: compiles, >= 10 trades on training data
Step 4: Tag descriptors
        - lineage: base_template + mutations applied
        - mechanism / complexity / turnover / holding descriptors
Step 5: Feed into Stage 3-5 pipeline
```

**Output**:
- Strategy variant library: `ape_variants/` directory with generated code
- `ape_manifest.json`: all variants, their lineage, mutations, smoke test results
- Each variant registered in STRATEGY_REGISTRY equivalent

**Scale management**:
- Per template × per mutation type: ~10-30 variants
- Total with 5 templates × 6 mutation types × 5 parameter settings: ~150-900
- Far smaller than GFS feature space — manageable within single campaign

**Integration with x38**:
- Runs in Phase A, alongside GFS
- Generated strategies implement Strategy ABC (Topic 005 Core Engine compatible)
- Each variant is a candidate in Stage 3-5 search
- ESP-01 descriptor tagging applies: variants get mechanism/complexity tags
- Lineage tracking feeds into ESP-02 phenotype memory

**Why this matters**: X12-X19 churn research manually explored 8 variations of
VTREND exit mechanism. APE automates this: "given VTREND E0, generate all
single-mutation variants" would have produced X14, X16, X17, X18 equivalents
without human ideation.

---

### 2.3 Cross-Domain Analogy Probe (CDAP)

**Purpose**: Inject insights from non-financial domains to seed novel feature
ideas that would not emerge from pure financial data manipulation.

**Input**:
- Curated domain catalog (human-maintained, AI-assisted):

| Domain | Key concepts | Financial mapping potential |
|--------|-------------|---------------------------|
| Signal processing | SNR, spectral analysis, matched filter, wavelet decomposition | Trend quality, noise estimation, pattern matching |
| Physics | Kinetic energy, momentum, potential energy, entropy, diffusion | Volume-weighted returns, price acceleration, mean reversion force |
| Information theory | Shannon entropy, mutual information, Kullback-Leibler divergence, entropy rate | Regime detection, surprise measurement, distribution shift |
| Ecology | Carrying capacity, predator-prey dynamics, population cycles | Overbought/oversold, sentiment cycles, crowding |
| Network science | Centrality, clustering coefficient, flow betweenness | Cross-asset influence, correlation structure, information flow |
| Control theory | PID controller, feedback loops, stability margins | Adaptive filters, error correction, overshoot detection |

- Mapping rules per domain (human-curated):
  - Concept → mathematical formulation
  - Mathematical formulation → financial primitives substitution
  - Expected behavior (when should this signal fire?)

**Process**:
```
Step 1: Human researcher selects 1-2 domains per campaign
        (guided by EPC weak signals — see §3.3)
Step 2: AI generates mapping proposals:
        - Domain concept → mathematical formula
        - Formula → feature using financial primitives
        - Expected trading signal interpretation
Step 3: Human reviews mappings (reject nonsensical, approve plausible)
Step 4: Approved mappings → feature implementations
Step 5: Implementations enter Feature Engine registry (tagged origin: "cdap_[domain]")
Step 6: GFS can compose CDAP features with existing features (cross-pollination)
```

**Output**:
- `cdap_mappings.json`: domain, concept, formula, feature_id, human_approved
- Implemented features in Feature Engine with "cdap_" prefix
- Traceability: every CDAP feature traces back to domain + concept + mapping

**Concrete examples** (illustrative, not pre-validated):

| Domain | Concept | Formula | Feature name | Interpretation |
|--------|---------|---------|-------------|----------------|
| Physics | Kinetic energy | ½ × volume × return² | `cdap_kinetic_energy` | High when large volume + large price move |
| Info theory | Entropy rate | H(returns, rolling_window) | `cdap_return_entropy` | Low entropy = trending, high = noisy |
| Signal proc | SNR | abs(ema(returns)) / std(returns) | `cdap_trend_snr` | Trend strength relative to noise |
| Ecology | Carrying capacity | (price - ema_long) / atr | `cdap_carrying_deviation` | How far price is from "equilibrium" |
| Control theory | PID integral | cumsum(price - ema) over lookback | `cdap_integral_error` | Accumulated deviation from trend |

**Integration with x38**:
- CDAP is a **curated input** to Feature Engine, not an automated pipeline
- Human researcher is gatekeeper (Tier 3 authority): reviews and approves mappings
- CDAP features enter same registry as hand-written and GFS features
- Online/Offline boundary: mapping generation is online (AI + human conversation);
  feature implementation and evaluation is offline (pipeline)
- Does NOT contaminate: CDAP expands search space with novel features, does not
  inject priors about which features will win

**Why this matters**: VDO is essentially a cross-domain concept: order flow
analysis (market microstructure domain) applied to trend-following (technical
analysis domain). Systematic cross-domain probing increases the probability of
finding such cross-pollination insights.

---

### 2.4 Structured Serendipity Sessions (SSS)

**Purpose**: Deliberately recreate the conditions under which VDO was discovered —
AI sessions with loose constraints and creative mandate.

**Input**:
- Data snapshot (same as campaign data, no contamination risk from different data)
- Current Feature Engine registry (to avoid re-discovering known features)
- Loose prompt template (see below)
- Optional: domain hints from CDAP, weak signals from EPC

**Prompt template** (v1 — subject to debate):
```
You have access to OHLCV data for BTC/USDT from 2017-08 to 2026-02
at H4 and D1 resolution.

Current known features (DO NOT re-propose these):
[list of registered feature names + brief descriptions]

Task: Propose [N] novel trading signals that are NOT in the current
registry. For each proposal:
1. Name and one-line description
2. Mathematical formula using available primitives (OHLCV)
3. Expected behavior: when does it fire? What market condition?
4. Why it might work for trend-following on BTC
5. Domain origin (if inspired by another field)

Constraints:
- Each signal must be computable from OHLCV data only
- No forward-looking computation
- Prefer signals with clear causal story over "data-mined" patterns
- Diversity: proposals should cover different mechanism types

[Optional domain hint]: Focus especially on [domain_hint] concepts.
[Optional weak signal]: Consider investigating patterns related to
[epc_observation].
```

**Process**:
```
Step 1: Run M independent AI sessions (M >= 3)
        - Different AI models if available (diversity of reasoning)
        - Different temperature settings (creativity vs precision)
        - Different domain hints per session
Step 2: Collect all proposals (M × N total)
Step 3: Dedup
        - Remove proposals identical to existing features (string + semantic match)
        - Remove proposals identical to each other (cross-session dedup)
Step 4: Human screen
        - Quick pass: reject obviously nonsensical proposals
        - Grade remaining: plausible / speculative / interesting-but-unclear
Step 5: Implement approved proposals
        - Write @feature functions
        - Register in Feature Engine with "sss_" prefix
Step 6: Feed into campaign pipeline (Stage 3 scan)
```

**Output**:
- `sss_proposals.json`: all proposals, source session, human grade, implementation status
- Implemented features in Feature Engine with "sss_" prefix
- `sss_session_log/`: raw AI session transcripts (for reproducibility audit)

**Scale**: M=3 sessions × N=10 proposals = 30 raw proposals → after dedup and
screening → typically 5-15 novel features per SSS round.

**Integration with x38**:
- SSS runs in **Phase A** (pre-pipeline), explicitly online
- Compatible with `online_vs_offline.md` distinction:
  - SSS is an **online** activity with clear purpose (feature generation)
  - SSS output (implemented features) enters **offline** pipeline
  - SSS does NOT replace offline pipeline — it feeds it
- SSS does NOT contaminate:
  - Features expand search space (no priors about winners)
  - AI sessions do NOT see previous campaign results (firewall compliant)
  - Session transcripts are audit trail, not knowledge transfer
- SSS can be informed by EPC (§3.3) weak signals: "investigate volume patterns"
- SSS frequency: once per campaign (Phase A), optional repeat if
  NO_ROBUST_IMPROVEMENT

**Why this matters**: This is the direct recreation of VDO's origin story.
Instead of waiting for accidental prompts, SSS runs deliberate creative
sessions. The key insight: **you can't automate serendipity, but you can
increase its surface area**.

---

## 3. Tier 2: Recognition & Systematization Mechanisms

### 3.1 Surprise Detection Layer (SDL)

**Purpose**: Automatically flag unexpected results during pipeline execution
(Stages 3-6) that would be discarded by standard Sharpe-ranked pruning.

**Surprise criteria** (multi-dimensional — a candidate is flagged if it triggers
ANY criterion):

| Criterion | Definition | Threshold | Rationale |
|-----------|-----------|-----------|-----------|
| **Risk-profile outlier** | Sharpe < cell median BUT MDD < cell-best MDD × 0.7 | MDD ratio < 0.7 | Different risk/return profile worth investigating |
| **Decorrelation outlier** | Max |correlation| with all cell-elite survivors < 0.3 | corr < 0.3 | True diversifier — rare and valuable |
| **Regime specialist** | Performance in 1-2 regimes > 2× cell median, other regimes ≈ 0 | regime_sharpe > 2× median | May be useful as regime-conditional component |
| **Plateau champion** | Plateau width > 2× cell median plateau width | width > 2× median | Extremely robust to parameter changes |
| **Behavioral anomaly** | Feature behavior contradicts expected direction | empirical vs expected sign flip | May reveal unknown market mechanism |
| **Cost-invariant** | Performance ranking unchanged across 3+ cost scenarios | rank stable ± 2 | Real edge, not cost artifact |

**Process**:
```
Stage 3 scan completes → all candidates scored
Stage 4 begins:
  Step 4.1: Cell-elite archive selection (ESP-01 standard process)
  Step 4.2: SDL scan — check ALL candidates against surprise criteria
  Step 4.3: Flagged candidates get "surprise slot" in cell-elite archive
            (additional slot per cell, not replacing regular survivors)
  Step 4.4: Log to surprise_log.json
```

**Output**:
- `surprise_log.json` per session:
  ```json
  {
    "session_id": "s001",
    "flagged_count": 7,
    "surprises": [
      {
        "candidate_id": "gfs_ema_vol_ratio_20",
        "cell": "SINGLE_LOW_SWING",
        "criteria_triggered": ["decorrelation_outlier", "plateau_champion"],
        "sharpe": 0.42,
        "mdd": 18.3,
        "max_correlation_with_survivors": 0.12,
        "plateau_width": 3.2,
        "cell_median_plateau": 1.1,
        "human_review_required": false
      }
    ]
  }
  ```
- Surprise candidates preserved in cell-elite archive → continue to Stage 5-6

**Integration with x38**:
- SDL is a sub-component of ESP-01 (intra-campaign illumination)
- Runs within Stage 4 (after scan, during pruning)
- Does NOT change pruning criteria — adds extra preservation slots
- Budget: surprise slots capped at 20% of cell-elite capacity (ESP-04 compatible)
- Surprise candidates go through same Stage 5-6 evaluation as regular candidates

### 3.2 Three-Step Validation Protocol for Surprises

When SDL flags a candidate, it enters a structured validation funnel:

**Step 1 — Automated Sanity Check**:

| Check | Pass criterion | Automated? |
|-------|---------------|------------|
| Lookahead test | Zero violations | Yes |
| Minimum trades | >= 30 trades in evaluation window | Yes |
| Uniqueness | Correlation < 0.90 with all known features | Yes |
| Not artifact | Survives 500-iteration bootstrap resampling (p < 0.10) | Yes |
| Computability | No future data, no impossible operations | Yes |

Fail any check → discard (logged in surprise_log.json with failure reason).

**Step 2 — Mechanism Investigation** (semi-automated):

| Analysis | Output | Automated? |
|----------|--------|------------|
| Ablation | ΔSharpe, ΔMDD when feature removed from strategy | Yes |
| Regime decomposition | Sharpe per regime (6 regimes from VTREND research) | Yes |
| Cost sensitivity | Sharpe at 5 cost levels (10, 20, 30, 50, 100 bps) | Yes |
| Paired comparison | vs baseline (E0 or best known) with bootstrap CI | Yes |
| Causal story | Why does this work? Domain interpretation | Human review |

Output: `mechanism_report.json` per candidate with all analysis results.

**Step 3 — Integration Decision** (human + framework):

| Outcome | Condition | Action |
|---------|-----------|--------|
| **Proceed** | Step 2 all pass, mechanism clear | Enter Stage 5-6 normally |
| **Flag** | Step 2 mixed/ambiguous | Human researcher reviews mechanism_report |
| **Taxonomy extension** | Novel mechanism not in descriptor taxonomy | Propose ESP-01 descriptor addition |
| **EPC entry** | Interesting but too weak for current campaign | Record in Emergent Pattern Catalog |
| **Discard** | Step 2 shows artifact or non-robust | Log and drop |

**Integration with x38**:
- Steps 1-2 automated within pipeline (Stage 4-5 boundary)
- Step 3 is human checkpoint (Tier 3 authority, per 3-tier model)
- Output feeds into ESP-02 (CandidatePhenotype) for phenotype memory
- Output feeds into EPC (§3.3) for weak signal accumulation

### 3.3 Emergent Pattern Catalog (EPC)

**Purpose**: Track weak signals and structural observations across campaigns,
even when individual instances are too weak to produce a strategy.

**Distinction from ESP-02 (CandidatePhenotype)**:
- ESP-02 records candidates that **passed** pipeline evaluation — strong enough
  to be phenotyped
- EPC records **patterns** that are interesting but sub-threshold — observations
  that may accumulate evidence across campaigns

**EPC entry schema**:
```json
{
  "pattern_id": "epc_001",
  "observation": "Volume-weighted features consistently rank top-10 in Stage 3
                  across 3 campaigns but never survive Stage 5 architecture search",
  "descriptor_tags": ["flow", "compound", "medium_turnover"],
  "evidence": [
    {
      "campaign_id": "c001",
      "session_id": "s003",
      "candidate_ids": ["gfs_vol_momentum_20", "sss_vol_direction_40"],
      "stage_3_rank": [4, 7],
      "stage_5_outcome": "dropped",
      "sharpe": [0.38, 0.31]
    },
    {
      "campaign_id": "c002",
      "session_id": "s001",
      "candidate_ids": ["gfs_vol_ema_spread_30"],
      "stage_3_rank": [3],
      "stage_5_outcome": "dropped",
      "sharpe": [0.41]
    }
  ],
  "hypothesis": "Volume-based signals may be supporting features, not primary.
                 Consider testing as FILTER (not entry) in next campaign.",
  "action_items": [
    "APE: generate FILTER_ADD mutations using volume features on VTREND templates",
    "CDAP: probe market microstructure domain for volume-based filter concepts"
  ],
  "reconstruction_risk": 0.15,
  "created_at": "2026-04-15",
  "last_updated": "2026-06-20",
  "status": "ACCUMULATING"
}
```

**Firewall compliance**:
- EPC entries NEVER contain: feature names with parameter values, winner IDs,
  exact thresholds, calibration results
- EPC entries contain: descriptor-level tags, mechanism categories, directional
  observations ("top-10" not "Sharpe=0.38")
- Reconstruction-risk gate (ESP-02) applies: if descriptor bundle uniquely
  identifies a specific feature, coarsen descriptors
- EPC is descriptor-level memory (not answer-level) — compatible with F-01
  "inherit methodology, not answers"

**Accumulation rules**:
- New observation matching existing pattern_id → append to evidence array
- Contradiction (pattern reverses in new campaign) → update status to
  "CONTRADICTED", log contradiction evidence
- Pattern with evidence from 3+ campaigns → promote to "MATURE", eligible to
  influence CDAP domain selection and GFS grammar expansion
- Pattern with 0 new evidence for 3+ campaigns → update status to "DORMANT"

**Feedback loops** (EPC → Tier 1 mechanisms):
- EPC "MATURE" patterns → CDAP domain selection (probe related domains deeper)
- EPC "MATURE" patterns → GFS grammar expansion (add operators related to
  pattern mechanism)
- EPC "MATURE" patterns → SSS domain hints (include pattern observation in
  prompt)
- EPC "MATURE" patterns → APE mutation hints (generate variants that test
  pattern hypothesis)

**Integration with x38**:
- EPC is an extension of ESP-02 scope (phenotype memory for weak signals)
- EPC entries stored in `knowledge/epc/` directory (per design_brief §5)
- EPC is written at Stage 8 (same as epistemic_delta.json)
- EPC is read at Phase A (Tier 1 mechanisms use EPC as input)
- MK-17 compatible: EPC on same-dataset = SHADOW only (influences ordering/hints,
  not certification or pruning decisions)

---

## 4. Gap Analysis: What x38 Is Missing

### Gap 1: No search space expansion mechanism (CRITICAL)

**Problem**: x38 assumes Feature Engine registry is pre-populated. Protocol
Engine scans declared space exhaustively. But no component **creates** novel
features or architectures.

**Impact**: If VDO is not in declared space, framework cannot find it. This is
the single largest structural gap in x38.

**Evidence**:
- F-08 (Feature Engine) defines registry format but not generation mechanism
- F-05 (Protocol Engine) Stage 3 "single-feature scan" scans `registry` — but
  who populates registry?
- Topic 017 ESP improves search within declared space but does not expand it
- V4→V8 online sessions relied on AI creativity to propose new features — x38
  offline pipeline has no equivalent

**Solution**: Topic 018 (proposed, §5.1) — Search Space Expansion Policy

### Gap 2: No Phase A / Phase B separation

**Problem**: x38 conflates "deciding what to search" with "how to search" in
Protocol Engine. These are fundamentally different:
- **Expansion** (Phase A): creative, generative, online-compatible, non-deterministic
- **Execution** (Phase B): deterministic, exhaustive, offline, reproducible

**Impact**: Without separation, there's no clean place to plug in GFS, APE, SSS,
or CDAP. They don't fit into any of the 8 stages.

**Evidence**:
- online_vs_offline.md establishes the paradigm distinction but doesn't address
  the bridge between them
- design_brief §4 Campaign Model describes research phases but all phases are
  within offline pipeline
- No topic owns the "how does search space get declared" question

**Solution**: Amend Campaign Model (Topic 001 already CLOSED — may need
addendum) or define Phase A in Topic 018

### Gap 3: ESP-01 lacks surprise detection

**Problem**: ESP-01 improves coverage tracking and cell-elite archive.
Optimization criterion is Sharpe-centric (top survivors per cell). No mechanism
flags candidates that are interesting for non-Sharpe reasons.

**Impact**: Low-Sharpe but low-MDD candidates, decorrelated candidates,
regime-specialist candidates — all pruned in Stage 4 without investigation.

**Evidence**:
- ESP-01 cell-elite archive keeps "diverse survivors per cell" but diversity is
  within Sharpe-ranked top-K
- btc-spot-dev research history: LATCH and SM strategies (alternative profiles)
  were discovered manually, not by pipeline — they would have been pruned

**Solution**: SDL (§3.1) as ESP-05 addition to Topic 017

### Gap 4: No online-offline bridge

**Problem**: online_vs_offline.md correctly distinguishes paradigms. But x38
designs only the offline side. VDO discovery was online. No mechanism bridges
online creativity into offline pipeline.

**Impact**: x38 becomes a closed system that can only evaluate what's already
declared. The most creative phase (feature ideation) is left outside the
framework.

**Evidence**:
- online_vs_offline.md §5 checklist only checks whether online patterns apply
  to offline — doesn't address how online creativity feeds offline pipeline
- SSS (§2.4) addresses this gap explicitly

**Solution**: SSS as part of Topic 018 with clear online/offline contract

### Gap 5: Feature Engine lacks automated composition

**Problem**: F-08 defines registry for individual features. VDO =
`volume × direction` — a composition of 2 primitives. No mechanism to
automatically compose features.

**Impact**: Feature space limited to what humans explicitly write. Combinations
that seem "obvious" in hindsight (like VDO) are missed.

**Evidence**:
- F-08 lists families (trend, volatility, location, flow, structure, cross_tf)
  but no "composite" family
- GFS (§2.1) addresses this directly

**Solution**: Extend F-08 scope or add GFS to Topic 018

### Gap 6: No weak signal accumulation

**Problem**: ESP-02 records phenotypes for candidates that passed pipeline. But
weak signals that didn't pass are lost — even if they consistently appear across
campaigns.

**Impact**: Patterns that are individually sub-threshold but collectively
informative (e.g., "volume features always rank high but never win") are never
recorded or acted upon.

**Evidence**:
- ESP-02 CandidatePhenotype contract requires pipeline passage
- epistemic_delta.json (ESP-01) records coverage and gaps but not pattern-level
  observations
- btc-spot-dev research: volume indicator patterns accumulated across V4→V8 but
  were only noticed because human researcher remembered them across AI sessions

**Solution**: EPC (§3.3) as ESP-02 extension in Topic 017

---

## 5. Concrete Proposals for x38

### 5.1 NEW: Topic 018 — Search Space Expansion Policy

**Rationale**: Gaps 1, 2, 4, 5 all point to the same structural absence. No
existing topic owns the "how does search space get created/expanded" question.

**Scope**:

Topic 018 owns the **Phase A** of campaign lifecycle: mechanisms that expand
Feature Engine registry and strategy candidate pool before Protocol Engine
(Phase B) begins execution.

Specifically:
1. **GFS**: Grammar definition, depth limits, dedup rules, scale management,
   progressive deepening policy
2. **APE**: Mutation operator catalog, template format, lineage tracking, smoke
   test requirements
3. **SSS**: Prompt templates, session count/diversity requirements, human
   screening protocol, online/offline contract
4. **CDAP**: Domain catalog maintenance, mapping rules, curation process,
   interaction with EPC
5. **Phase A/B boundary**: When does expansion end? What triggers transition to
   execution? Contract with Protocol Engine (Topic 003)
6. **Budget allocation**: How much campaign compute goes to Phase A (expansion)
   vs Phase B (execution)? Interaction with ESP-04 budget governor

**Findings** (proposed):
- **F-36**: Generative Feature Synthesis — grammar, operators, scale management
- **F-37**: Architecture Perturbation Engine — mutations, templates, lineage
- **F-38**: Structured Serendipity Sessions — online/offline bridge contract
- **F-39**: Cross-Domain Analogy Probe — domain catalog, mapping rules
- **F-40**: Phase A/B boundary — transition contract, budget split

**Scope boundaries with existing topics**:

| Topic | Boundary |
|-------|----------|
| 006 (Feature Engine) | 006 owns registry format + family taxonomy. 018 owns generation mechanism feeding INTO registry. |
| 017 (ESP) | 017 owns intra-pipeline search efficiency (Phase B). 018 owns pre-pipeline expansion (Phase A). EPC feedback loop crosses boundary — 018 reads EPC, 017 writes EPC. |
| 003 (Protocol Engine) | 003 owns 8-stage pipeline (Phase B). 018 defines Phase A and the A→B transition contract. |
| 008 (Architecture) | 008 owns pillar count and identity. If 008 elevates ESP to 4th pillar, 018 may become sub-component of ESP. If 008 keeps 3 pillars, 018 is independent pre-pipeline component. |
| 005 (Core Engine) | 005 owns Strategy ABC. APE-generated strategies must implement Strategy ABC — 018 consumes, 005 defines. |

**Dependencies**:
- **Upstream**: Topic 007 (philosophy — "inherit methodology" principle applies),
  Topic 008 (architecture — pillar structure)
- **Downstream**: Topic 006 (generated features enter registry),
  Topic 003 (Phase A feeds Phase B), Topic 017 (EPC feedback loop)
- **No hard dependency** on 001 (CLOSED) or 002 (CLOSED) — Phase A expansion
  does not touch firewall or campaign structure (it runs BEFORE pipeline)

**Wave assignment**: Wave 2 (parallel with 005, 006, 008). Must close before
Topic 003 (Wave 3).

**Debate plan**:
- Estimated: 2-3 rounds (4 mechanisms + boundary definition)
- Key battles:
  - GFS grammar: how deep? How to control explosion?
  - APE: mutation operators sufficient? How to ensure generated code quality?
  - SSS: how to prevent SSS from becoming backdoor contamination? Online/offline
    contract must be airtight
  - Phase A/B budget: 20%/80%? 10%/90%? Evidence-based calibration?
  - CDAP: useful or YAGNI for v1?

**Burden of proof**: Mixed. GFS + APE are structural gaps (burden on opponents
to show they're unnecessary). SSS + CDAP are enhancements (burden on proposer
to show value).

**Cross-topic tensions**:

| Topic | Tension | Resolution path |
|-------|---------|-----------------|
| 006 | GFS auto-generates features — does this conflict with F-08 hand-written registry pattern? | 006 defines contract; 018 defines generation. Same @feature format. |
| 017 | EPC feedback loop: 018 reads EPC to guide expansion, 017 writes EPC. Circular dependency? | No: temporal ordering. Campaign N writes EPC (017). Campaign N+1 reads EPC (018). Same as MK-17 shadow-only principle. |
| 002 | SSS involves AI sessions — does this violate offline paradigm? | SSS is explicitly online (Phase A). Output (features) is offline. Contract must ensure no answer-level contamination flows through. |
| 008 | If 008 rejects 4th pillar and keeps 3, where does 018 live architecturally? | 018 lives as pre-pipeline component, not a pillar. Substance exists regardless of architectural framing. |

---

### 5.2 ADD to Topic 017: ESP-05 (Surprise Detection Layer)

**Rationale**: Gap 3. Cell-elite archive pruning is Sharpe-centric. Surprises
need explicit preservation mechanism.

**Proposed finding**:

```
## ESP-05: Surprise Detection Layer

- issue_id: X38-ESP-05
- classification: Thiếu sót
- opened_at: 2026-03-25
- opened_in_round: 0
- current_status: Open

Multi-dimensional surprise criteria (§3.1 of this document) applied during
Stage 4 cell-elite archive selection. Surprise candidates get additional
preservation slots. surprise_log.json as Stage 4 mandatory output.

Three-step validation protocol (§3.2) for flagged candidates:
automated sanity check → mechanism investigation → integration decision.
```

**Scope interaction with existing ESP findings**:
- ESP-01: SDL runs within cell-elite archive mechanism (additive, not replacing)
- ESP-04: Surprise slots consume budget (capped at 20% of cell capacity)

---

### 5.3 EXTEND ESP-02: Emergent Pattern Catalog

**Rationale**: Gap 6. Weak signals lost between campaigns.

**Proposed extension** to ESP-02 scope:

```
ESP-02 currently defines CandidatePhenotype (strong signals that passed
pipeline) and StructuralPrior (knowledge objects for search policy).

Extension: add Emergent Pattern Catalog (EPC) as third artifact type.
EPC records weak signals and structural observations that are individually
sub-threshold but may accumulate evidence across campaigns.

EPC contract: firewall compliant (descriptor-level only), reconstruction-risk
gated (ESP-02 gate applies), accumulation rules for cross-campaign evidence.

EPC feedback loop to Phase A mechanisms (Topic 018): CDAP domain hints,
GFS grammar expansion, SSS prompt hints, APE mutation hints.
```

---

### 5.4 EXTEND Topic 006 (F-08): Automated Feature Composition

**Rationale**: Gap 5. Feature Engine lacks composition mechanism.

**Proposed additions to F-08 scope**:

1. **Grammar-based composition**: Define operators that combine features into
   composite features. Interaction with GFS (Topic 018) — GFS provides the
   generation engine, F-08 provides the registration contract.

2. **Feature importance diagnostics**: Beyond Sharpe ranking in Stage 3:
   - Mutual information with forward returns
   - Granger causality tests
   - Permutation importance (shuffle feature, measure performance drop)
   - These diagnostics feed into SDL surprise criteria

3. **Feature interaction detection**: Automatically test feature pairs/triples:
   - Test `feature_A AND feature_B` (joint filter)
   - Test `feature_A THEN feature_B` (sequential condition)
   - Flag pairs with super-additive performance (combined > sum of individual)

---

## 6. Implementation Priority & Phasing

### v1 (First campaign — minimum viable discovery)

| Component | Include? | Rationale |
|-----------|----------|-----------|
| GFS depth 1 | YES | Low complexity, high value. ~500-2000 new features |
| APE single-mutation | YES | Automates what X12-X19 did manually |
| SSS 3 sessions | YES | Direct VDO recreation, low cost |
| CDAP | DEFER v2 | Useful but requires curated domain catalog — build catalog first |
| SDL | YES | Simple criteria, high value for preserving surprises |
| 3-step validation | YES | Steps 1-2 automated, Step 3 human |
| EPC | DEFER v2 | Need multiple campaigns to accumulate evidence |
| Promotion ladder | DEFER v2 | Per ESP-03: inert on same dataset |

### v2 (After first campaign, with campaign evidence)

| Component | Include? | Rationale |
|-----------|----------|-----------|
| GFS depth 2 | CONDITIONAL | Only if depth 1 yields NO_ROBUST_IMPROVEMENT |
| CDAP | YES | Domain catalog built during v1, ready to deploy |
| EPC | YES | v1 campaign provides first evidence batch |
| EPC feedback loops | YES | EPC → GFS/SSS/APE/CDAP influence |
| Promotion ladder (ESP-03) | PARTIAL | Storage (OBSERVED, REPLICATED_SHADOW) active |

### v3+ (Multiple campaigns, possibly new data)

| Component | Include? | Rationale |
|-----------|----------|-----------|
| GFS depth 3 | CONDITIONAL | Only if depth 1-2 insufficient |
| Full promotion ladder | YES | Context distance > 0 enables ACTIVE rungs |
| Inter-campaign EPC influence | YES | Mature patterns guide expansion |
| Automated CDAP mapping | EXPERIMENTAL | AI-generated domain mappings without human curation |

---

## 7. Evaluation: How to Know if This Works

**Pre-registered success criteria** (measure after v1 campaign):

| Metric | Definition | Target |
|--------|-----------|--------|
| **Discovery yield** | % of IRC candidates that originated from Phase A (GFS/APE/SSS) vs hand-declared features | > 20% |
| **Surprise preservation rate** | % of SDL-flagged candidates that pass 3-step validation | > 10% |
| **Coverage expansion** | Ratio of total features evaluated (with Phase A) vs declared features (without Phase A) | > 3× |
| **Diversity index** | Descriptor-space entropy of Stage 4 cell-elite archive | Higher than baseline (declared-only) |
| **Novelty rate** | % of Phase A features with correlation < 0.3 to ALL declared features | > 30% |

**Aspiration metric** (v2+):
- P(strong solution) = P(IRC) × P(CLEAN_OOS | IRC)
- Compare: campaigns with Phase A vs campaigns without Phase A (matched compute budget)
- This requires multiple campaigns — pre-register criteria now, measure later

---

## 8. Compatibility Matrix

| x38 Invariant | Compatible? | Notes |
|---------------|-------------|-------|
| F-01: "Inherit methodology, not answers" | YES | Phase A expands search space (methodology). Does not inject priors about winners (answers). |
| MK-17: Same-dataset shadow-only | YES | EPC on same-dataset = shadow influence only (ordering/hints). GFS/APE/SSS do not use prior campaign results. |
| F-22: Phase 1 evidence types | YES | Phase A artifacts are coverage/process evidence (Type 1). |
| F-04: Firewall typed schema | YES | GFS/APE features enter same registry with same schema. SSS contract prevents answer leakage. |
| D-16: Protocol identity change → new campaign | YES | Phase A mechanisms don't change protocol identity. They change search space, which is a campaign input, not protocol. |
| C-12: Answer priors banned always | YES | Phase A generates features (search space), not priors about which features win. |
| Topic 001 Campaign Model | COMPATIBLE | Phase A runs before Phase B within same campaign. Does not change campaign structure. |
| Topic 002 Firewall | COMPATIBLE | SSS online/offline contract must be explicit. GFS/APE are purely computational — no contamination vector. |

---

## 9. Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| GFS feature explosion | HIGH | Progressive deepening (depth 1 first). Hard cap per depth level. Dedup threshold 0.95. |
| SSS as contamination backdoor | HIGH | SSS contract: AI sessions see only OHLCV data + current registry. Never see previous campaign results. Output = features, not priors. |
| Multiple testing with expanded space | HIGH | Stricter FDR at Stage 3→4. F-05 open question about scan-phase correction becomes more urgent. |
| CDAP nonsensical mappings | MEDIUM | Human gatekeeper (Tier 3). Only approved mappings enter pipeline. |
| APE generating bad code | MEDIUM | Smoke test (compile + minimum trades). Type checking. Same Strategy ABC contract. |
| Phase A consuming too much budget | MEDIUM | Phase A budget cap (debate: 10-20% of campaign compute). ESP-04 governor applies. |
| EPC ratchet (weak signals never cleared) | LOW | DORMANT status after 3 campaigns with no new evidence. Periodic audit. |

---

## 10. Relationship to VDO Discovery

To close the loop on the motivating story:

| VDO discovery element | x38 mechanism |
|----------------------|---------------|
| AI prompt → novel feature idea | SSS (deliberate creative sessions) |
| Volume × direction = novel composition | GFS (grammar-based feature composition) |
| Cross-domain insight (order flow × trend) | CDAP (cross-domain analogy probing) |
| Accidental discovery, not planned | SDL (surprise detection for unexpected results) |
| Later proved valuable through backtesting | 3-step validation protocol |
| Recognized as useful only after many experiments | EPC (weak signal accumulation) |
| VDO became permanent component of E5 | ESP-02 phenotype → Feature Engine integration |

**The key reframe**: VDO was not a single lucky accident. It was the product of
(1) creative feature ideation, (2) novel composition, (3) cross-domain thinking,
(4) surprise recognition, and (5) rigorous validation. Each of these steps can
be systematized without destroying the serendipity that made VDO possible.

The goal is not to eliminate chance — it's to **maximize the surface area** where
chance can operate, while ensuring that when chance delivers, the framework
**recognizes and validates** the result.
