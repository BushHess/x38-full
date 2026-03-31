# Discovery Specification — Alpha-Lab Framework

**Status**: DRAFT (2026-03-31, expanded from SEEDED state with Topic 019 proposals)
**Source**: `debate/018-search-space-expansion/final-resolution.md` (§1-§5 v1),
`debate/019-discovery-feedback-loop/findings-under-review.md` (§6-§11 v2 proposals)
**Dependencies**: Topic 018 (CLOSED), Topic 019 (OPEN — §6-§11 pending debate)

> This spec covers discovery mechanisms: how Alpha-Lab generates, recognizes,
> and integrates new candidates.
>
> **§1-§5**: v1 mechanisms (bounded ideation, recognition, APE). Traced to
> Topic 018 decisions. Authoritative — 018 CLOSED.
>
> **§6-§11**: v2 mechanisms (data profiling, grammar expansion, pre-filter,
> statistical budget, human-AI loop, feature graduation). Proposals from
> Topic 019, pending debate. NOT authoritative until 019 CLOSED.
>
> Together, §1-§5 + §6-§11 form the complete discovery architecture:
> v1 = mechanical search within declared space (validation factory)
> v2 = human-AI collaborative discovery of new feature concepts (R&D lab)

---

## §1 Bounded Ideation (SSE-D-02, SSE-D-03)

### 1.1 Hard Rules

All ideation (pre-lock candidate generation) must satisfy 4 hard rules:

1. **Results-blind** — ideation sees NO results from any session (past or current)
2. **Compile-only** — output must compile (syntactically valid strategy spec)
3. **OHLCV-only** — only OHLCV + volume data as input features
4. **Provenance-tracked** — every generated candidate records its generation method

Violation of any rule = candidate rejected at generation gate. No exceptions.

### 1.2 Generation Modes

Two modes available at protocol lock:

| Mode | Activation | Description |
|------|-----------|-------------|
| `grammar_depth1_seed` | Always available (mandatory default) | Deterministic grammar enumeration producing depth-1 seeds from declared building blocks |
| `registry_only` | Conditional — requires 3 guards | Re-use candidates from existing registry without new generation |

### 1.3 Cold-Start Activation (`registry_only`)

`registry_only` mode requires ALL 3 conditions:
1. Registry is **non-empty** (at least 1 candidate exists)
2. Registry is **frozen** (no active modifications)
3. Registry is **`grammar_hash`-compatible** (structural compatibility verified)

If any condition fails, fall back to `grammar_depth1_seed`.

### 1.4 Grammar-Provenance Admissibility

Grammar-provenance admissibility policing (what constitutes valid provenance
for a generated candidate) belongs in Topics 002/004 (contamination firewall),
not in the discovery spec. This spec defines generation modes; the firewall
spec defines what provenance records are admissible.

**Trace**: SSE-D-02, SSE-D-03 → `debate/018-search-space-expansion/final-resolution.md` Decision 2

---

## §2 Recognition Stack (SSE-D-05)

### 2.1 Pre-Freeze Recognition Topology

The recognition pipeline processes unexpected results through 4 stages:

```
surprise_queue → equivalence_audit → proof_bundle → freeze
```

- **surprise_queue**: Candidates flagged by anomaly detection enter a queue
  for structured evaluation
- **equivalence_audit**: Determines whether a surprise is genuinely novel
  or equivalent to a known candidate (uses hybrid equivalence per §5)
- **proof_bundle**: Assembles required evidence for the surprise candidate
  (5 proof components, see §2.3)
- **freeze**: Candidate promoted to frozen status with complete proof bundle

**Topology boundary**: This pipeline stops at `freeze`. Post-freeze stages
(`freeze_comparison_set → candidate_phenotype → contradiction_registry`) are
scoped to downstream topics (017, 003, 015) and are NOT part of the discovery
spec.

### 2.2 Working Minimum Inventory — Anomaly Axes

5 anomaly axes define the dimensions along which surprise is detected:

1. `decorrelation_outlier` — candidate returns decorrelated from known families
2. `plateau_width_champion` — candidate shows unusually wide parameter plateau
3. `cost_stability` — candidate performance unusually stable across cost scenarios
4. `cross_resolution_consistency` — candidate consistent across timeframe resolutions
5. `contradiction_resurrection` — candidate contradicts a previously dismissed hypothesis

### 2.3 Working Minimum Inventory — Proof Components

5 proof components required for a surprise candidate's proof bundle:

1. `nearest_rival_audit` — comparison against closest known candidate
2. `plateau_stability_extract` — evidence of parameter stability
3. `cost_sensitivity_test` — performance across cost scenarios
4. `dependency_stressor` — robustness under dependency perturbation
   (alias: `ablation_or_perturbation_test` — valid concrete form)
5. `contradiction_profile` — relationship to contradicted prior results

### 2.4 Inventory Governance

- The 5+5 named inventory is a **working minimum** adopted at **Judgment call
  authority** (not Converged). It is NOT an immutable historically-converged
  exact label set.
- **Thresholds**: Owned by Topics 017 (epistemic search policy) and 013
  (convergence analysis). This spec defines WHAT is measured, not HOW MUCH
  is enough.
- **Expansion**: Adding axes or components beyond the minimum requires an
  explicit downstream finding. The minimum is a floor, not a ceiling.

**Trace**: SSE-D-05 → `debate/018-search-space-expansion/final-resolution.md` Decision 4 → human researcher judgment

---

## §3 APE v1 Scope (SSE-D-11)

### 3.1 Template Parameterization Only

APE (Automated Parameter Exploration) v1 is limited to:
- Filling declared template parameters with values from declared ranges
- Producing candidates that satisfy all 4 hard rules (§1.1)

### 3.2 Excluded from v1

- **No free-form code generation** — correctness guarantee absent in v1
- **No indicator composition** — no combining arbitrary indicators into new ones
- **No runtime code evaluation** — all generation is compile-time only

### 3.3 v2+ Pathway

Free-form code generation is a v2+ capability, gated on:
- A verification mechanism being designed and validated
- Firewall integration for generated code provenance

**Trace**: SSE-D-11 → `debate/018-search-space-expansion/final-resolution.md` Decision 10

---

## §4 Domain-Seed Hook (SSE-D-10)

### 4.1 Optional Provenance Hook

Domain-seed is an **optional** provenance hook that records the domain context
(e.g., "this candidate was inspired by mean-reversion literature") as metadata.

### 4.2 Excluded

- **No replay semantics** — domain-seed does not enable replaying a generation process
- **No session format** — no structured session representation for domain seeds
- **No catalog infrastructure** — no centralized domain-seed registry

### 4.3 Composition Provenance

Composition provenance (how components were combined to form a candidate) is
preserved via lineage tracking (SSE-D-07, routed to Topic 015), not through
domain-seed replay.

**Trace**: SSE-D-10 → `debate/018-search-space-expansion/final-resolution.md` Decision 9

---

## §5 Hybrid Equivalence (SSE-D-06)

### 5.1 Two-Layer Equivalence

Candidate equivalence is determined by a deterministic hybrid method:

1. **Structural pre-bucket** (fast, deterministic):
   - Descriptor hash
   - Parameter family membership
   - AST-hash subset
   - Groups candidates into structural buckets

2. **Behavioral nearest-rival audit** (within buckets):
   - Compare performance profiles of structurally-similar candidates
   - Detect functional equivalence despite structural differences
   - Deterministic: thresholds are part of the equivalence definition

### 5.2 Constraints

- **No LLM judge** — equivalence must be fully deterministic
- **Versioned determinism** — thresholds are versioned with the equivalence
  definition; changing thresholds = new equivalence version
- **Thresholds and invalidation** — exact values deferred to downstream topics
  (008: interface, 013: semantics, 017: consumption)

**Trace**: SSE-D-06 → `debate/018-search-space-expansion/final-resolution.md` Decision 5

---

---

# V2 Discovery Mechanisms (Topic 019 — PENDING DEBATE)

> **Authority**: Everything below is a PROPOSAL from Topic 019
> (OPEN, 2026-03-29). NOT authoritative until debate closure.
> Sections §6-§11 may be modified, simplified, or rejected by debate.

> **Architectural motivation**: v1 (§1-§5) provides a validation factory —
> mechanical search within a declared space. v2 (§6-§11) adds an R&D lab —
> human-AI collaborative discovery of new feature concepts. The binding
> constraint on discovery is statistical power (§9), not search technology.
> v2 makes this constraint explicit and designs around it.

---

## §6 Data Profiling Layer (DFL-10)

### 6.1 Stage 2.5 — Data Characterization

Insert between Stage 2 (Data audit, integrity) and Stage 3 (Feature scan,
grammar-defined). Stage 3 is BLOCKED until `data_profile.json` exists.

| Property | Value |
|----------|-------|
| Position | After Stage 2, before Stage 3 |
| Input | `audit_report.json` (Stage 2), raw data files |
| Output | `data_profile.json` |
| Gate | Stage 3 blocked until output exists |
| Compute ceiling | < 30 minutes (profiling, not investigation) |
| Scope | Descriptive statistics only — NO causal interpretation |

### 6.2 `data_profile.json` Contents

| Section | Contents | Purpose |
|---------|----------|---------|
| `field_inventory` | All fields, dtypes, basic stats (count, mean, std, min, max, nulls) | Know what data exists |
| `distributional_profile` | Per field: normality test, stationarity test, structural break count | Know data properties before grammar design |
| `pairwise_dependencies` | Rank correlation matrix + MI for all numeric field pairs | Identify informative fields and redundancies |
| `temporal_structure` | Autocorrelation summary per field (significant lags at α) | Know temporal properties for feature design |
| `coverage_map` | `grammar_fields` vs `all_fields`, `coverage_ratio`, ungovered fields flagged | Make grammar gaps visible to protocol |

### 6.3 What This Is NOT

- NOT a "causal story gate" (018 rejected). Machine-computable descriptive statistics.
- NOT the full DFL-06 suite. Stage 2.5 = shallow profiling (< 30 min). DFL-06 = deep investigation (days).
- NOT a modifier of SSE-D-02. Grammar (Stage 3) remains OHLCV-only. Stage 2.5 profiles ALL fields for awareness.
- NOT a blocker on interpretation. Gate is mechanical: `data_profile.json` exists → Stage 3 unblocked.

### 6.4 Design Alternative

Topic 003 may fold characterization INTO Stage 2 instead of adding Stage 2.5.
DFL-10 proposes a separate stage; 003 owns the final decision on stage count.

**Trace**: DFL-10 → `debate/019-discovery-feedback-loop/findings-under-review.md`

---

## §7 Grammar Depth-2+ Composition (DFL-12, DFL-09, DFL-03)

### 7.1 Depth Levels

v1 grammar (§1) is depth-1: `feature = f(field, lookback)`.
v2 extends to depth-2+ with composition operators:

```
Depth-1 (v1): feature = f(field, lookback)
  Example: ema(close, 21)

Depth-2 (v2): feature = f(g(field_a, n), g(field_b, m))
  Example: ratio(ema(taker_buy_vol, 14), ema(total_vol, 14))
  Note:    ^^^ This IS VDO expressed as grammar composition

Depth-3 (v2+): feature = f(g(h(...)))
  Example: zscore(ratio(ema(taker_buy_vol, 14), ema(total_vol, 14)), 20)
```

### 7.2 Composition Operators

v2 adds these operators to the grammar building blocks:

| Operator | Signature | Purpose |
|----------|-----------|---------|
| `ratio` | (Series, Series) → Series | Relative comparison (VDO pattern) |
| `diff` | (Series, Series) → Series | Absolute difference |
| `zscore` | (Series, int) → Series | Standardization over rolling window |
| `rank` | (Series, int) → Series | Percentile rank over rolling window |

**Excluded operators** (per DFL-12):
- `crossover`: produces BoolSeries (signal), not composable Series
- `lag`: redundant with lookback parameter extension

### 7.3 Search Space Estimation

**Depth-1 base features**: `base_op(field, lookback)`

```
6 base operators × 5 OHLCV fields × 10 lookbacks = 300 features
```

**Depth-2 composition**: `comp_op(depth1_a, depth1_b)` or `comp_op(depth1, window)`

| Composition type | Operator | Operands | Count (OHLCV) |
|-----------------|----------|----------|---------------|
| Binary, non-commutative | `ratio` | 300 × 299 ordered pairs | 89,700 |
| Binary, anti-symmetric | `diff` | C(300,2) unordered | 44,850 |
| Unary + window | `zscore`, `rank` | 300 × 10 windows × 2 ops | 6,000 |
| **Total depth-2 (OHLCV)** | | | **~140,000** |

| Depth | Estimated configs |
|-------|-------------------|
| 1 (v1, OHLCV) | ~300 |
| 2 (v2, OHLCV-only grammar) | ~140,000 |
| 2 (v2, human template all 13 fields) | ~950,000 |
| 3 (v2+) | combinatorial explosion → human template only |

**Implication**: ~140K depth-2 OHLCV features is substantial. Pre-filtering (§8)
must reduce this by ~99.5% to be tractable for human review. This sets the
performance requirement for Tier 0 screening.

Depth-3 is combinatorially explosive → v2 stops at depth-2 for automated
grammar. Depth-3 via human template only (DFL-03 channel 1).

### 7.4 SSE-D-02 Scope for Grammar vs Human Templates

Per DFL-09 scope clarification:

| Activity | SSE-D-02 rule 3 (OHLCV-only) | Fields available |
|----------|------------------------------|------------------|
| Grammar depth-2 enumeration | YES — applies | 5 OHLCV fields |
| Human-originated template | NO — human decides | All 13 fields |
| DFL-06 analysis / DFL-01 AI layer | NO — analysis, not ideation | All 13 fields |

**Asymmetry is intentional**: Grammar has combinatorial enumeration as sole
quality gate → restrict to OHLCV to limit search space. Human templates have
human judgment (Tier 3) as quality gate → no field restriction needed.

**Implication**: VDO-type features (using `taker_buy_vol`, a non-OHLCV field)
can ONLY enter via human template, not via grammar enumeration. This matches
how VDO was actually discovered — human insight, not mechanical search.

### 7.5 Pruning for Equivalent Compositions

~140K depth-2 features contain structural redundancies:

- **Self-compositions**: `ratio(ema(close, 21), ema(close, 21))` = constant 1.0
- **Same-field same-op pairs**: `ratio(ema(close, 21), ema(close, 50))` and
  `diff(ema(close, 21), ema(close, 50))` are different features despite same
  inputs — ratio is scale-free, diff is not. Do NOT prune as equivalent.
- **Degenerate lookbacks**: `zscore(ema(close, 3), 3)` with window ≤ lookback
  produces near-constant output.

**Pruning strategy** (two-stage):
1. **Structural pruning** at generation time: remove self-compositions,
   degenerate lookbacks, and structurally identical features (§5 hash).
   Expected reduction: ~140K → ~80-100K.
2. **Behavioral de-duplication** after MI screening: features with pairwise
   ρ > 0.95 (§9.2 equivalence threshold) collapsed to representative.
   Applied only to §8 pre-filter survivors, not to full candidate set.

**Trace**: DFL-09, DFL-03 → `debate/019-discovery-feedback-loop/findings-under-review.md`

---

## §8 Information-Theoretic Pre-Filter (DFL-08 Stage 1, DFL-11 Tier 0)

### 8.1 Purpose

Pre-filter reduces grammar-generated candidate features from thousands to
tens WITHOUT consuming statistical budget (§9). This is the mechanism that
makes depth-2 grammar tractable despite N=188 trades.

### 8.2 Two-Tier Screening Model

| Tier | Activity | Metric | Budget cost | Output |
|------|----------|--------|-------------|--------|
| **Tier 0** | Pre-filter (screening) | MI ranking | **Reduced** (see §8.4) | Ranked candidate list |
| **Tier 1** | Formal validation (decision) | WFO, bootstrap, Sharpe | **Full — 1 unit per feature** | PASS/FAIL verdict |

### 8.3 Tier 0 Pre-Filter Specification

**Primary metric**: Mutual Information (MI) between candidate feature and
forward returns.

**Why MI**:
- Captures ALL dependence (linear + non-linear), unlike IC (linear only)
- Distribution-free (no normality assumption)
- MI = 0 ⟺ statistical independence (both directions)

**Gate**: Top-N features by MI rank, where N is a fixed constant declared
before screening (not data-dependent). Default proposal: N = 200.

**Why fixed-N, not p-value threshold**: A p-value gate (e.g., MI > 0 at
p < 0.10) IS a binary decision, not a ranking. Under H0 (all features
noise), 10% of ~140K = 14,000 would pass by chance — the "gate" lets
through too many. Fixed-N ranking avoids this: take top 200 regardless of
significance. The multiple testing cost comes from the N survivors entering
Tier 1, not from the ranking itself.

**Implementation**:

```
For each candidate feature f in grammar_depth2_features:
    mi[f] = mutual_information(f, forward_returns)

# Rank by MI, take top N (declared before screening)
candidates = sorted(features, key=mi, reverse=True)[:N]
```

### 8.4 Budget Cost of Tier 0 Screening

**Tier 0 is NOT free.** The honest model:

The screening step DOES introduce selection bias — features with high MI
are more likely to also have high Sharpe, because MI and Sharpe both measure
the feature-return relationship (through different lenses). Screening by MI
and then testing by Sharpe is NOT independent screening.

**What Tier 0 DOES achieve**: It reduces the Tier 1 test count from ~140K
to N (e.g., 200). The FWER correction at Tier 1 is Holm over N tests, not
over 140K. This is the real value — not "free" but "much cheaper."

**What Tier 0 costs**: The selection bias from MI-based screening inflates
the expected Sharpe of survivors under H0. This means Tier 1 p-values are
ANTI-CONSERVATIVE (true false positive rate > nominal α). The magnitude
of this inflation is an **empirical question** — it depends on the
MI-Sharpe correlation, which must be measured on real data.

**Mitigation**: Two approaches (debate should decide):

| Approach | Mechanism | Cost |
|----------|-----------|------|
| **Permutation calibration** | Compute MI on permuted returns (1000×). The MI rank threshold that passes α=0.10 under permutation becomes the Tier 0 cutoff. | Computationally expensive (~140K × 1000 permutations) |
| **Conservative inflation factor** | Apply a fixed multiplier (e.g., 2×) to Tier 1 α to compensate for selection bias. Calibrate factor empirically on synthetic data. | Requires simulation study to determine factor |

**Open question for debate**: The exact cost of Tier 0 screening is an
EMPIRICAL question, not a theoretical one. A simulation study (generate
synthetic features with known MI/Sharpe properties, run the two-tier
pipeline, measure actual false positive rate) is needed to calibrate the
inflation factor. This is a code task, not a spec task.

### 8.5 Expected Reduction

| Input | Tier 0 output (N=200) | Reduction |
|-------|----------------------|-----------|
| ~140,000 depth-2 OHLCV features | 200 candidates (top by MI rank) | 99.86% |
| ~950,000 depth-2 all-fields | 200 candidates (same N) | 99.98% |

Survivors go to human review (DFL-08 Stage 3), then formal validation (§9).

**Note**: The 200 survivors INCLUDE many false positives (features that
rank high by chance). Human review (Stage 3) is the next filter — domain
judgment reduces 200 to ~3-10 worth testing formally.

**Trace**: DFL-08, DFL-11 → `debate/019-discovery-feedback-loop/findings-under-review.md`

---

## §9 Statistical Budget Accounting (DFL-11)

### 9.1 The Binding Constraint

The ceiling on feature discovery is NOT search technology — it is
**statistical power** given finite data.

The available power depends critically on WHICH test is used:

| Test | Effective N | Power driver | Regime |
|------|------------|--------------|--------|
| Trade-level paired test | ~188 trades | Large N, moderate effect | K_max potentially large |
| WFO Wilcoxon (8 folds) | 8 folds | Tiny N, must have large effect | K_max very small |
| Bootstrap CI | 1000 resamples | Good for point estimate, weak for comparison | Intermediate |

**The WFO bottleneck**: The project's validation pipeline uses WFO Wilcoxon
with 8 folds as a binding gate. At N=8, even detecting Δ_Sharpe = 0.30
requires near-certainty (power ≈ 0.37 at α=0.05 for single test). This
means WFO power is already below 50% at K=1. Adding features makes it worse.

**This is NOT a theoretical problem — it is the ACTUAL problem with E5-ema21D1**:
WFO Wilcoxon p=0.125 > α=0.10. The algorithm is HOLD because WFO has
insufficient power to confirm it, despite strong full-sample evidence.

**Implication**: The budget constraint depends on which gate is binding.
If WFO is the binding gate (as currently), K_max ≈ 1-3 for any effect size.
If trade-level tests are used (or WFO is reformed), K_max is much larger.
This is an EMPIRICAL question requiring power simulation on real data.

### 9.2 Budget Tracker Schema

```
StatisticalBudget:
  dataset_params:
    n_trades: int
    timespan_years: float
    m_eff: float                # Nyholt effective DOF
  budget:
    alpha_fwer: float           # Family-wise error rate (0.05)
    k_tested: int               # Features formally tested
    k_max_estimate: int         # Max tests at min_detectable_effect
    min_detectable_effect: float # Current Δ_Sharpe threshold at 80% power
  ledger: list[BudgetEntry]

BudgetEntry:
    feature_id: str
    test_date: date
    test_metric: str            # sharpe, wfo_wilcoxon, bootstrap_ci
    p_value: float
    effect_size: float
    holm_adjusted_alpha: float  # α at time of test
    verdict: str                # PASS / FAIL
    notes: str
```

### 9.3 Budget Rules

1. **Tier 0 pre-filter = zero formal budget units (selection bias acknowledged)**:
   MI screening, IC ranking, DFL-06 analyses, Stage 2.5 profiling.
   Does NOT charge a formal budget unit to the Holm correction counter.
   Selection bias exists (§8.4) and must be mitigated, but is NOT modeled
   as a discrete test in the budget ledger.
2. **Tier 1 formal test = costs 1 unit**: Each feature entering full
   validation (DFL-08 Stage 5) consumes 1 unit. Holm correction adjusts
   α for cumulative k_tested.
3. **Human override**: If budget exhausted, human researcher (Tier 3) may
   authorize additional tests with acknowledged reduced power. Recorded.
4. **Per-dataset scope**: Budget resets when new data arrives (Clean OOS
   Phase 2 or new research Phase 3). Previous dataset budget archived.
5. **Separate from grammar scan**: Topic 013 Holm correction applies to
   grammar_depth1_seed (50K+ configs). Discovery loop features have own
   budget. Rationale: grammar tests within DECLARED space; discovery tests
   NOVEL features. Pooling penalizes both.
6. **Redundancy deduction**: Feature correlating r > 0.95 with already-tested
   feature → 0 budget cost (variant, not new test). Per Topic 013 SSE-04-THR.

### 9.4 Budget Lifecycle in DFL-08 Graduation Path

```
DFL-06 Analyses ──────── [Tier 0, reduced cost — selection bias acknowledged]
        │
DFL-08 Stage 1 ──────── [Tier 0, MI ranking, top-N selection]
        │
DFL-08 Stage 2 ──────── [Tier 0, deep dive, characterization]
        │
DFL-08 Stage 3 ──────── [No cost, human judgment]
        │
DFL-08 Stage 4 ──────── [No cost, registry bookkeeping]
        │
DFL-08 Stage 5 ──────── [Tier 1, COSTS 1 BUDGET UNIT]
        │                   │
        │          ┌────────┴────────┐
        │          │ Budget check:    │
        │          │ Power sufficient? ── YES → run validation
        │          │                  └── NO  → WARN, human decides
        │          └─────────────────┘
        ▼
Budget ledger: k_tested += 1, Holm α_adj recalculated
```

### 9.5 Why the Loop Is Human-AI, Not Fully Automated

With limited statistical power, K must be kept small. Two mechanisms:

1. **Pre-filter (§8)** reduces grammar candidates from ~140K to ~200
   mechanically (MI ranking).
2. **Human review (DFL-08 Stage 3)** reduces ~200 to ~3-10 using domain
   judgment before formal testing.

The human's role is practical: the pre-filter alone passes too many
candidates for the budget. Domain judgment is the second filter.

**Caveat**: The claim that "human intuition keeps K small by selecting
features based on economic reasoning" is a post-hoc narrative from
btc-spot-dev history. VDO was tested as K=1 not because the human KNEW
it would work, but because it was tested first. Many features with
equally compelling economic reasoning (regime conditioning, complexity,
short-side) were also tested and failed. The competitive advantage of
human judgment is PLAUSIBLE but UNPROVEN — it is a design assumption,
not an established fact.

**Trace**: DFL-11 → `debate/019-discovery-feedback-loop/findings-under-review.md`

---

## §10 Human-AI Collaboration Loop (DFL-01 through DFL-05)

### 10.1 Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                 STATISTICAL BUDGET (§9)              │
│  K_max features | K_used spent | α_adj current      │
└───────────────────────┬─────────────────────────────┘
                        │
     ┌──────────────────▼──────────────────┐
     │    AI ANALYSIS LAYER (DFL-01)       │
     │    ─────────────────────────        │
     │    Input: raw data + validation     │
     │           results (results-aware)   │
     │    Method: DFL-07 toolkit           │
     │    Output: DiscoveryReport (DFL-02) │
     │    Budget cost: Reduced (Tier 0)     │
     └──────────────────┬──────────────────┘
                        │ Structured findings
     ┌──────────────────▼──────────────────┐
     │    HUMAN REVIEW (DFL-08 Stage 3)    │
     │    ─────────────────────────        │
     │    Decisions: INVESTIGATE |         │
     │      TEMPLATE | GRAMMAR | DISCARD   │
     │    Authority: Tier 3 (human)        │
     │    Budget cost: ZERO                │
     └──────────────────┬──────────────────┘
                        │ 1-3 candidates (K kept small)
     ┌──────────────────▼──────────────────┐
     │    HUMAN-AI DELIBERATION (DFL-05)   │
     │    ─────────────────────────        │
     │    Multiple discussion rounds       │
     │    Convergence gate: both agree     │
     │    Output: design specification     │
     │    Budget cost: ZERO                │
     └──────────────────┬──────────────────┘
                        │ Converged design
     ┌──────────────────▼──────────────────┐
     │    CODE AUTHORING (DFL-05)          │
     │    ─────────────────────────        │
     │    AI writes code after convergence │
     │    Human reviews + approves         │
     │    Provenance-tracked               │
     │    Budget cost: ZERO                │
     └──────────────────┬──────────────────┘
                        │ Strategy implementation
     ┌──────────────────▼──────────────────┐
     │    VALIDATION PIPELINE (§9 Tier 1)  │
     │    ─────────────────────────        │
     │    Full 7-gate validation           │
     │    Budget cost: 1 UNIT              │
     │    Holm-adjusted α for K_used tests  │
     └──────────────────┬──────────────────┘
                        │
                  PROMOTE / HOLD / REJECT
```

### 10.2 AI Analysis Layer Properties (DFL-01)

| Property | Value |
|----------|-------|
| Results-aware | YES — reads all pipeline outputs |
| Data-aware | YES — reads raw market data (all 13 fields) |
| SSE-D-02 applies | NO — analysis, not ideation (per DFL-09) |
| Output type | Process observations (Type 1 evidence, F-22) |
| Can modify pipeline | NO — parallel observer only |
| Can generate code | NO — analysis only (SSE-D-11) |
| Trigger | On-demand (human request) or post-validation (automatic) |

**Two analysis domains**:

| Domain | Analyzes | Discovery type |
|--------|----------|---------------|
| Result analysis | Backtest outputs, validation metrics | "This strategy behaves unexpectedly" |
| Data analysis | Raw market data, microstructure | "This data feature is unusual" |

### 10.3 Report Contract (DFL-02)

```
DiscoveryReport:
  run_id: str
  timestamp: datetime
  scope: AnalysisScope
  findings: list[Finding]       # Ordered by estimated importance

Finding:
  finding_id: str               # DFL-YYYYMMDD-NNN
  category: PatternCategory     # statistical | mathematical | economic |
                                # structural | anomaly
  confidence: ConfidenceLevel   # high | medium | low
  summary: str                  # 1-2 sentence human-readable
  evidence: Evidence
  suggested_investigation: str
  contamination_class: str      # process_observation (always)
```

### 10.4 Feedback Channels (DFL-03)

| Channel | What human provides | Contamination | Budget cost |
|---------|--------------------|----|-----|
| New template | Strategy template with declared parameters | Provenance-tracked, NOT results-blind | 0 (creation) → 1 (validation) |
| Grammar extension | New building blocks for grammar_depth1_seed | MUST be results-blind (SSE-D-02) | 0 (addition) → covered by grammar scan budget |
| Investigation directive | Question for analysis layer | No contamination concern | 0 |

### 10.5 Deliberation-Gated Code Authoring (DFL-05)

| Property | Value |
|----------|-------|
| Initiator | Human always |
| Process | Multi-round discussion → convergence |
| Convergence gate | Both sides agree on WHAT + WHY |
| Code author | AI (after convergence), human reviews |
| Validation | Normal pipeline, no special treatment |
| Provenance | Links to deliberation artifact |

**Relationship to SSE-D-11**: DFL-05 is NOT an exception to SSE-D-11 (APE v1
no-code-gen). It is a SEPARATE mechanism. SSE-D-11 governs AUTOMATED generation.
DFL-05 governs HUMAN-INITIATED, CONVERGENCE-GATED authoring. Different trigger,
different gate, different scope.

### 10.6 Contamination Model (DFL-04)

| Stage | What flows | Contamination class |
|-------|-----------|-------------------|
| Pipeline → AI Analysis | Metrics, trades, equity curves | Results (exempt from SSE-D-02 — analysis, not ideation) |
| AI Analysis → Human | Structured findings | Process observations (Type 1) |
| Human → Template | Strategy specification | Provenance-tracked, NOT results-blind |
| Human → Grammar | New primitives | MUST pass results-blind test |
| Deliberation | Design discussion | Results-aware (analysis) |
| Code → Pipeline | Strategy implementation | Normal pipeline input (all gates) |

**Why this is NOT contamination laundering**: Human is always the gateway.
AI analysis never directly modifies pipeline. Analysis outputs are process
observations, not answer priors. Everything enters normal validation.

**Trace**: DFL-01 through DFL-05 → `debate/019-discovery-feedback-loop/findings-under-review.md`

---

## §11 Feature Graduation Pipeline (DFL-08)

### 11.1 End-to-End Path

5-stage path from "pattern discovered in raw data" to "feature registered
and available for strategy generation":

```
Stage 1: Discovery → Candidate       [Tier 0, zero formal units]
Stage 2: Candidate → Deep Dive       [Tier 0, zero formal units]
Stage 3: Report → Human Decision     [No cost]
Stage 4: Human Decision → Registry   [No cost]
Stage 5: Registry → Validation       [Tier 1, costs 1 unit]
```

### 11.2 Stage Details

**Stage 1: Discovery → Candidate**

- Input: DFL-06 analysis output (Phase 1 SCAN) OR §7 grammar depth-2 output
- Gate: Top-N by MI rank (N declared before screening, per §8.3)
- Output: `feature_candidate` record

**Stage 2: Candidate → Deep Dive Report**

- Input: feature_candidate
- Gate: DFL-07 Phase 2 passes (distributional, structural break, null model p < 0.05)
- Output: Finding in DFL-02 DiscoveryReport

**Stage 3: Report → Human Decision**

- Input: DiscoveryReport finding
- Decisions: INVESTIGATE (loop to Stage 2) | TEMPLATE (DFL-03) | GRAMMAR (DFL-03) | DISCARD
- Authority: Human researcher (Tier 3). AI CANNOT promote.

**Stage 4: Human Decision → Feature Registry**

- Input: TEMPLATE or GRAMMAR decision
- Gate: F-08 (Topic 006) registry acceptance
- Output: Feature registered with `source: discovery_loop` + provenance chain
- `generation_mode`: `human_template` or `grammar_extension`

**Stage 5: Registry → Strategy Validation**

- Input: Registered feature from Stage 4
- Gate: Full validation pipeline (7 gates)
- Budget: Costs 1 unit from §9 budget tracker
- Output: PROMOTE / HOLD / REJECT

### 11.3 Governance

| Property | Value |
|----------|-------|
| Human veto | Any stage (Tier 3) |
| AI authority | Stage 1-2 only (screening + deep dive) |
| Budget check | Before Stage 5 (warn if budget exhausted) |
| Multiple testing | Holm-corrected across all Stage 5 tests (§9) |
| Provenance | End-to-end: analysis → candidate → report → decision → registry → verdict |

**Trace**: DFL-08 → `debate/019-discovery-feedback-loop/findings-under-review.md`

---

## Traceability

| Section | Issue ID | Source |
|---------|----------|--------|
| §1.1-1.2 Hard Rules + Modes | SSE-D-02 | `debate/018-search-space-expansion/final-resolution.md` Decision 2 |
| §1.3 Cold-Start | SSE-D-03 | `debate/018-search-space-expansion/final-resolution.md` Decision 2 |
| §2.1 Topology | SSE-D-05 | `debate/018-search-space-expansion/final-resolution.md` Decision 4 |
| §2.2-2.3 Inventory | SSE-D-05 | `debate/018-search-space-expansion/final-resolution.md` Decision 4 (Judgment call) |
| §3 APE v1 | SSE-D-11 | `debate/018-search-space-expansion/final-resolution.md` Decision 10 |
| §4 Domain-Seed | SSE-D-10 | `debate/018-search-space-expansion/final-resolution.md` Decision 9 |
| §5 Equivalence | SSE-D-06 | `debate/018-search-space-expansion/final-resolution.md` Decision 5 |
| §6 Data Profiling | DFL-10 | `debate/019-discovery-feedback-loop/findings-under-review.md` (PENDING) |
| §7 Grammar Depth-2+ | DFL-12 (primary), DFL-09, DFL-03 | `debate/019-discovery-feedback-loop/findings-under-review.md` (PENDING) |
| §8 Pre-Filter | DFL-08, DFL-11 | `debate/019-discovery-feedback-loop/findings-under-review.md` (PENDING) |
| §9 Statistical Budget | DFL-11 | `debate/019-discovery-feedback-loop/findings-under-review.md` (PENDING) |
| §10 Human-AI Loop | DFL-01–DFL-05 | `debate/019-discovery-feedback-loop/findings-under-review.md` (PENDING) |
| §11 Feature Graduation | DFL-08 | `debate/019-discovery-feedback-loop/findings-under-review.md` (PENDING) |
