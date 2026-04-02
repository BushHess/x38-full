# Findings Under Review — Statistical Budget

**Topic ID**: X38-T-19D2
**Opened**: 2026-04-02
**Author**: human researcher

1 finding about statistical budget accounting — how finite validation capacity
constrains discovery, two-tier screening design, and budget lifecycle. Split
from Topic 019D (DFL-11). Single finding but ~250 lines with its own internal
structure (budget model, two-tier screening, lifecycle, accounting rules).

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
- 019A (DFL-04/05/09): Foundational boundary decisions — DFL-09 scope
  classification determines what counts as "analysis" vs "ideation", which
  affects DFL-11's scope of budget accounting.

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

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 006 | F-08 | Feature registry — DFL-11 proposes budget_spent field in registry metadata | DFL-11 proposes; F-08 (006) defines registry schema |
| 013 | SSE-09 (Holm) | Grammar scan correction vs discovery loop budget — separate pools? | DFL-11 defines discovery-specific budget; 013 owns grammar-scan correction |

---

## Decision summary — what debate must resolve

Debate for Topic 019D2 must produce decisions on these questions. All are Tier 3
(depend on 019A Tier 1 foundational decisions being resolved first).

**Tier 3 — Budget & governance**:

| ID | Decision | Finding | Alternatives |
|----|----------|---------|-------------|
| D-09 | Separate budget for discovery vs grammar scan? | DFL-11 | Separate (disjoint families) / Pooled (single FWER) |
| D-10 | Retroactive counting of pre-framework tests? | DFL-11 | Clean start (k=0) / Full accounting / Partial (selected) |
| D-11 | How to handle Tier 0 selection bias? | DFL-11 | Permutation calibration / Conservative factor / Simulation study first |

---

## Summary table

| Issue ID | Finding | Classification | Status |
|----------|---------|---------------|--------|
| X38-DFL-11 | Statistical budget accounting (two-tier screening) | Thiếu sót | Open |
