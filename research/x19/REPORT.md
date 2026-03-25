# X19: Alternative Actuators for Churn Score — Report

**Date**: 2026-03-10
**Verdict**: CLOSE (both branches fail G1, WFO 25% and 50%)

## Central Question

Can a different action policy for high-churn-score trail breaches — exit + re-enter
(Branch A) or partial runner (Branch B) — outperform static suppress (hold-through)?

## Results

### T0: Configuration Sweep (16 configs)

#### Branch A: Exit + Contingent Re-entry

| α | f_A | Sharpe | d_Sharpe | MDD% | Armed | Re-entry | Expired |
|---|-----|--------|----------|------|-------|----------|---------|
| 5% | 0.25 | 1.394 | +0.058 | 38.4 | 9 | 6 | 0 |
| 5% | 0.50 | 1.372 | +0.036 | 38.4 | 9 | 6 | 0 |
| 10% | 0.25 | 1.409 | +0.073 | 38.1 | 17 | 10 | 0 |
| 10% | 0.50 | 1.381 | +0.045 | 38.4 | 17 | 10 | 0 |
| **15%** | **0.25** | **1.445** | **+0.110** | **35.9** | 24 | 15 | 0 |
| 15% | 0.50 | 1.410 | +0.074 | 38.4 | 24 | 15 | 0 |
| 20% | 0.25 | 1.415 | +0.080 | 35.6 | 30 | 20 | 0 |
| 20% | 0.50 | 1.401 | +0.065 | 36.6 | 30 | 20 | 0 |

Best: α=15%, f_A=0.25, Sharpe=1.445 (+0.110 vs E0), MDD=35.9%.

**Key observation**: f_A=0.25 consistently beats f_A=0.50. Smaller re-entry position
reduces variance without losing much capture. MDD improvement is real (35.6-38.4%
vs E0's 42.0%).

#### Branch B: Partial Runner

| α | f_B | Sharpe | d_Sharpe | MDD% | Partial | Reclaim | Runner Exit |
|---|-----|--------|----------|------|---------|---------|-------------|
| 5% | 0.10 | 1.318 | -0.018 | 41.0 | 12 | 11 | 1 |
| **5%** | **0.25** | **1.326** | **-0.010** | **40.1** | 12 | 11 | 1 |
| 10% | 0.10 | 1.205 | -0.131 | 41.7 | 30 | 29 | 1 |
| 10% | 0.25 | 1.236 | -0.100 | 41.3 | 30 | 29 | 1 |
| 15% | 0.10 | 1.119 | -0.217 | 45.0 | 52 | 49 | 3 |
| 15% | 0.25 | 1.165 | -0.171 | 43.7 | 52 | 49 | 3 |
| 20% | 0.10 | 1.203 | -0.133 | 45.0 | 67 | 61 | 6 |
| 20% | 0.25 | 1.250 | -0.086 | 43.7 | 67 | 61 | 6 |

Best: α=5%, f_B=0.25, Sharpe=1.326 (-0.010 vs E0). **Cannot beat E0.**

**Key observation**: Reclaim triggers on almost all partial exits (11/12 at α=5%,
49/52 at α=15%), yet the strategy still underperforms. The cost of partial exit
(50 bps on 75-90% of position) plus add-back cost (50 bps on 75-90%) creates a
100+ bps round-trip cost per episode that overwhelms the runner's small capture.

### T1: Nested WFO (4 folds)

#### Branch A

| Fold | Year | Best Params | E0 Sharpe | X19 Sharpe | d_Sharpe | Result |
|------|------|-------------|-----------|------------|----------|--------|
| 1 | 2022 | α=20%, f=0.25 | -0.930 | -0.930 | -0.000 | LOSE |
| 2 | 2023 | α=20%, f=0.25 | 1.203 | 1.201 | -0.002 | LOSE |
| 3 | 2024 | α=20%, f=0.25 | 1.696 | 1.773 | +0.078 | WIN |
| 4 | 2025 | α=15%, f=0.25 | 0.069 | 0.069 | -0.000 | LOSE |

Win rate: **25%** (1/4), mean d_sharpe: **+0.019**

**G1: FAIL** (25% < 75%)

The armed re-entries simply don't trigger OOS in most folds. Fold 1 (2022 bear)
and Fold 4 (2025 choppy) produce zero delta — no trail stops get high enough
scores in the test period to arm re-entry.

#### Branch B

| Fold | Year | Best Params | E0 Sharpe | X19 Sharpe | d_Sharpe | Result |
|------|------|-------------|-----------|------------|----------|--------|
| 1 | 2022 | α=5%, f=0.25 | -0.930 | -0.930 | -0.000 | LOSE |
| 2 | 2023 | α=5%, f=0.25 | 1.203 | 1.203 | +0.000 | WIN |
| 3 | 2024 | α=5%, f=0.25 | 1.696 | 1.696 | +0.000 | LOSE |
| 4 | 2025 | α=5%, f=0.25 | 0.069 | 0.069 | +0.000 | WIN |

Win rate: **50%** (2/4), mean d_sharpe: **+0.000**

**G1: FAIL** (50% < 75%, mean d ≈ 0)

Branch B at α=5% is essentially a no-op — only 12 partial exits in the full
sample, and the OOS folds see almost none. The "wins" are noise at the 4th
decimal place.

### T5: Comparison

| Strategy | Sharpe | CAGR% | MDD% | Trades |
|----------|--------|-------|------|--------|
| E0 | 1.336 | 55.3 | 42.0 | 186 |
| X19_A (α=20%, f=0.25) | 1.415 | 57.2 | 35.6 | 187 |
| X18 (α=40%) | 1.482 | 66.6 | 41.8 | 147 |
| X14 D (P>0.5) | 1.428 | 64.0 | 36.7 | 133 |

## Gate Summary

| Gate | Condition | Branch A | Branch B |
|------|-----------|----------|----------|
| ABORT | Best > E0 | PASS | FAIL |
| G1 | WFO ≥ 75%, mean d > 0 | **FAIL** (25%) | **FAIL** (50%) |

(G2-G5 not reached — early termination at G1.)

## Why Alternative Actuators Fail

### 1. Cost asymmetry kills Branch B

Branch B (partial runner) exits 75-90% of the position at trail, keeping
10-25% as runner. Reclaim fires on almost all episodes (92% at α=5%).
But each cycle costs ~100 bps RT (partial exit + add-back). At α=15%,
52 episodes × ~100 bps ≈ 52 bps total drag — this is 4× the E0 round-trip
frequency, destroying any runner capture.

### 2. Branch A's MDD improvement doesn't survive WFO

Branch A achieves real MDD improvement in full sample (35.6% vs 42.0%).
But this is driven by a few specific episodes in the training period that
the model identifies correctly. OOS, the model scores too few episodes
above the α-threshold to make a difference — most folds see zero or near-zero
armed re-entries.

### 3. Static suppress is strictly better when the model is right

For episodes where the model correctly identifies churn (ΔU > 0):
- Static suppress: captures 100% of continuation at zero extra cost
- Branch A: captures 25-50% minus re-entry cost
- Branch B: captures 10-25% minus partial exit/add-back cost

There is NO scenario where alternative actuators beat static suppress on
positive-ΔU episodes. The only theoretical advantage is loss avoidance on
negative-ΔU episodes — but those are rare enough (P10 = -3.8%) that the
savings don't compensate.

### 4. The "score identifies continuation utility" premise is correct but irrelevant

The analyst's core insight — that the score correctly ranks continuation
utility — was verified by X18's T0 (Q5 median ΔU > 0). But this doesn't
mean a different actuator is needed. The score already works optimally with
static suppress. The actuator IS correct: hold through when the model says
the trail stop is churn.

## Decision

Per SPEC decision matrix: Both branches fail G1 → **CLOSE**.

**One-more-round commitment fulfilled**: Neither alternative actuator beats
static suppress. Churn research is COMPLETE.

Final churn filter landscape:
- **X18 (α=40%, static suppress)**: PROMOTED — return-focused (Sharpe 1.482)
- **X14 D (P>0.5, static suppress)**: PROMOTED — risk-focused (MDD 36.7%)
- **X19 (alt actuators)**: CLOSED — cannot improve on static suppress

Static suppress is the optimal and only viable actuator for the 7-feature
churn score model. No further actuator variants warranted.

## Artifacts

- `x19_results.json` — all test results
- `x19_sweep.csv` — T0 configuration sweep (16 configs)
- `x19_wfo_A.csv` — T1 WFO results Branch A
- `x19_wfo_B.csv` — T1 WFO results Branch B
- `x19_comparison.csv` — T5 strategy comparison
