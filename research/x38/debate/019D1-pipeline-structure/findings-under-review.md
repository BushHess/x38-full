# Findings Under Review — Pipeline Structure

**Topic ID**: X38-T-19D1
**Opened**: 2026-04-02
**Author**: human researcher

2 findings about pipeline structure — how discovered features graduate through
a defined path from raw pattern to registered feature, and how data
characterization integrates as a prerequisite pipeline stage. Split from
Topic 019D (DFL-08, DFL-10).

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

**Upstream dependencies within 019 split**:
- 019A (DFL-04/05/09): Foundational boundary decisions — contamination model,
  code authoring scope, SSE-D-02 analysis/ideation distinction. DFL-08
  contamination rules depend on 019A outcomes.
- 019B (DFL-01/02/03): Loop mechanisms — AI analysis layer, report contract,
  human feedback channels. DFL-08 graduation path connects these components.

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
**Gate**: Normal validation pipeline (all 7 gates — CLAUDE.md:156-174 [extra-archive])
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

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 003 | F-05 | Pipeline stages — **DFL-10 proposes Stage 2.5** between Stages 2-3 | 003 owns pipeline stage count. DFL-10 proposes; 003 decides |
| 006 | F-08 | Feature registry acceptance — DFL-08 Stage 4 + budget metadata | DFL-08 defines interface; DFL-11 (019D2) proposes budget_spent field; F-08 (006) defines registry schema |
| 015 | F-14 | DFL-10 proposes `data_profile.json` as new artifact | 015 owns artifact enumeration; DFL-10 proposes; 003 mediates |

---

## Decision summary — what debate must resolve

Debate for Topic 019D1 must produce decisions on these questions. All are Tier 2
(depend on 019A Tier 1 foundational decisions being resolved first).

**Tier 2 — Mechanisms**:

| ID | Decision | Finding | Alternatives |
|----|----------|---------|-------------|
| D-05 | Should the pre-filter use top-N ranking or p-value threshold? | DFL-08+DFL-11 (DFL-11 owned by 019D2) | Top-N (fixed, declared) / P-value (data-dependent) / Hybrid |
| D-07 | Stage 2.5 as new stage or expand Stage 2? | DFL-10 | New Stage 2.5 / Expand Stage 2 / Reject (not needed) |

---

## Summary table

| Issue ID | Finding | Classification | Status |
|----------|---------|---------------|--------|
| X38-DFL-08 | Feature candidate graduation path (5 stages) | Thiếu sót | Open |
| X38-DFL-10 | Pipeline integration: Stage 2.5 data characterization | Thiếu sót | Open |
