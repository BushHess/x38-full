# Report 18 — Current Inference Stack on Control Pairs

**Date**: 2026-03-03
**Artifacts**: `artifacts/18_current_stack_on_control_pairs.py`, `artifacts/18_current_stack_on_control_pairs.json`
**Depends on**: Report 17 (testbed selection)

---

## 1. Purpose

Evaluate whether the CURRENT project inference stack behaves sensibly
on three control pairs with known ground truth:

1. **Negative control**: VTREND_A0 vs VTREND_A1 (ΔSharpe = -0.006)
2. **Mid positive control**: VTREND_A0 vs VBREAK (ΔSharpe = +0.098)
3. **Strong positive control**: VTREND_A0 vs VCUSUM (ΔSharpe = +0.343)

A sensible inference stack should:
- FAIL the negative control (correctly: no significant difference)
- PASS the strong positive control (correctly: detect ΔSharpe = +0.343)

---

## 2. Methods Evaluated

### 2.1 Paired Block Bootstrap (`v10/research/bootstrap.py`)

- **Statistic tested**: Sharpe(A) - Sharpe(B) from resampled 4H returns
- **Null hypothesis**: no difference in Sharpe between A and B
- **Mechanism**: circular block bootstrap with same indices for both curves
- **Config**: 2000 replicates, seed 1337, block sizes {10, 20, 40}
- **Gate**: `p_a_better >= 0.80 AND ci_lower > -0.01` (primary block size)

### 2.2 Paired Block Subsampling (`v10/research/subsampling.py`)

- **Statistic tested**: annualized excess geometric growth (A vs B)
- **Null hypothesis**: annualized excess geometric growth ≤ 0
- **Mechanism**: overlapping block means of differential log-returns,
  Politis-Romano-Wolf CI via `sqrt(b) × (block_means - full_mean)`
- **Config**: block sizes {10, 20, 40}, deterministic (no seed)
- **Gate**: `median(p) >= 0.80 AND median(ci_lower) > 0.0 AND
  support_ratio >= 0.60`

### 2.3 Deflated Sharpe Ratio (`research/lib/dsr.py`)

- **Statistic tested**: per-strategy Sharpe with multiple-testing correction
- **Null hypothesis**: observed Sharpe ≤ expected max Sharpe from N trials
- **Mechanism**: Bailey & López de Prado (2014) moment-adjusted DSR
- **Config**: trial levels {27, 54, 100, 200, 500, 700}
- **Gate**: `dsr_pvalue > 0.95` for ALL trial levels
- **Note**: per-strategy, not paired. Evaluated on each strategy individually.

### 2.4 Permutation Tests (`research/multiple_comparison.py`)

- **Scope**: component-level (EMA, VDO, ATR), not pair-level
- **Not applicable** to pairwise strategy comparison
- **Prior results**: p_EMA = 0.0003, p_VDO = 0.0003, p_ATR = 0.0003
  (all survive Bonferroni at K=16)

---

## 3. Observed Strategy Metrics

| Strategy | Sharpe | CAGR | MDD | Trades |
|---|---|---|---|---|
| **VTREND_A0** | 1.276 | +52.7% | 41.5% | 189 |
| **VTREND_A1** | 1.283 | +52.6% | 41.7% | 188 |
| **VBREAK** | 1.179 | +35.2% | 34.0% | 69 |
| **VCUSUM** | 0.934 | +25.2% | 28.5% | 73 |

All strategies: sp=120, trail=3.0, ATR(14), cost 50bps RT, 2019-01-01 to
2026-02-20.

---

## 4. Raw Results

### 4.1 Negative Control: VTREND_A0 vs VTREND_A1

**Observed**: ΔSharpe = -0.006, ΔCAGR = +0.1%, ΔMDD = -0.2%

**Bootstrap (Sharpe):**

| Block | p_a_better | CI_lower | CI_upper | Δ_obs |
|---|---|---|---|---|
| 10 | 0.474 | -0.124 | +0.107 | -0.007 |
| 20 | 0.473 | -0.127 | +0.112 | -0.007 |
| 40 | 0.499 | -0.128 | +0.111 | -0.007 |

**Gate**: p=0.474 < 0.80 → **FAIL**. Correct.

**Subsampling:**

| Block | p_a_better | CI_lower | CI_upper | Δ_ann |
|---|---|---|---|---|
| 10 | 0.980 | +0.001 | +0.001 | +0.001 |
| 20 | 0.965 | -0.020 | +0.012 | +0.001 |
| 40 | 0.939 | -0.028 | +0.028 | +0.001 |

**Grid**: median_p=0.965, median_ci_lower=-0.020, support=0.33 → **FAIL**.
Correct, but note p_a_better is 0.97 — the subsampling DETECTS a directional
signal even in the negative control. The CI gate saves it from a false positive.

**DSR**: Both strategies fail at all trial levels (max_trials_passing = 0).

### 4.2 Mid Positive Control: VTREND_A0 vs VBREAK

**Observed**: ΔSharpe = +0.098, ΔCAGR = +17.5%, ΔMDD = +7.5%

**Bootstrap (Sharpe):**

| Block | p_a_better | CI_lower | CI_upper | Δ_obs |
|---|---|---|---|---|
| 10 | 0.644 | -0.454 | +0.638 | +0.098 |
| 20 | 0.644 | -0.438 | +0.651 | +0.098 |
| 40 | 0.648 | -0.468 | +0.668 | +0.098 |

**Gate**: p=0.644 < 0.80 → **FAIL**. Expected given small ΔSharpe.

**Subsampling:**

| Block | p_a_better | CI_lower | CI_upper | Δ_ann |
|---|---|---|---|---|
| 10 | 0.925 | -0.127 | +0.431 | +0.129 |
| 20 | 0.905 | -0.128 | +0.418 | +0.129 |
| 40 | 0.895 | -0.099 | +0.414 | +0.129 |

**Grid**: median_p=0.905, median_ci_lower=-0.127, support=0.00 → **FAIL**.
High p but all CIs include negative territory. Zero support ratio.

**DSR**: Both strategies fail at all trial levels.

### 4.3 Strong Positive Control: VTREND_A0 vs VCUSUM

**Observed**: ΔSharpe = +0.343, ΔCAGR = +27.5%, ΔMDD = +13.1%

**Bootstrap (Sharpe):**

| Block | p_a_better | CI_lower | CI_upper | Δ_obs |
|---|---|---|---|---|
| 10 | **0.818** | **-0.401** | +1.072 | +0.343 |
| 20 | 0.798 | -0.415 | +1.127 | +0.343 |
| 40 | 0.811 | -0.420 | +1.095 | +0.343 |

**Gate**: p=0.818 ≥ 0.80 (passes p!) BUT ci_lower=-0.401 < -0.01 → **FAIL**.
The bootstrap DETECTS the direction (82% of resamples agree A is better)
but the CI spans [-0.40, +1.07] — far too wide to declare significance.

**Subsampling:**

| Block | p_a_better | CI_lower | CI_upper | Δ_ann |
|---|---|---|---|---|
| 10 | 0.937 | -0.131 | +0.625 | +0.219 |
| 20 | 0.930 | -0.139 | +0.616 | +0.219 |
| 40 | 0.926 | -0.144 | +0.625 | +0.219 |

**Grid**: median_p=0.930, median_ci_lower=-0.139, support=0.00 → **FAIL**.
Very high directional probability (93%) but CI includes negative. Zero support.

**DSR**: Both strategies fail at all trial levels.

---

## 5. Decision Matrix

| Pair | Control Type | ΔSharpe | Bootstrap | Subsampling | DSR-A | DSR-B | Expected |
|---|---|---|---|---|---|---|---|
| A0 vs A1 | Negative | -0.006 | **FAIL** | **FAIL** | FAIL | FAIL | FAIL |
| A0 vs VBREAK | Mid positive | +0.098 | **FAIL** | **FAIL** | FAIL | FAIL | PASS |
| A0 vs VCUSUM | Strong positive | +0.343 | **FAIL** | **FAIL** | FAIL | FAIL | PASS |

**Every method fails on every pair.**

---

## 6. Diagnosis

### 6.1 Bootstrap: Correct Direction, No Power

The bootstrap correctly detects the directional signal:
- Negative control: p=0.47 (no direction) ✓
- Strong positive: p=0.82 (correct direction) ✓

But the 95% CI for the Sharpe difference spans [-0.40, +1.07] — a width of
1.47 Sharpe units. To pass the gate, the CI must not cross -0.01, meaning
the observed ΔSharpe must exceed ~0.75 or more. **No strategy pair in the
repo has a Sharpe difference that large.**

**Why the CI is so wide.** The Sharpe ratio is estimated from ~15,647 H4
returns over ~7 years. Despite the large bar count, the effective sample
size is much smaller because:
1. Trend-following returns are highly autocorrelated (long holding periods)
2. Circular block bootstrap with blocks of 10-40 preserves this correlation
3. BTC returns have high kurtosis (~10-20 for H4), inflating Sharpe variance
4. The strategies are in-position only ~21-47% of the time, reducing the
   number of informative bars

The bootstrap is doing its job correctly — it is honestly reporting the
enormous uncertainty in Sharpe estimation from 7 years of H4 data. The
problem is that the CI gate (`ci_lower > -0.01`) demands near-certainty
that the gate cannot deliver at any achievable sample size.

### 6.2 Subsampling: Suspicious p_a_better + Correct CI

The subsampling shows a curious pattern:
- **Negative control**: p_a_better = 0.97 — nearly "certain" A0 beats A1
- **Strong positive**: p_a_better = 0.93 — less "certain" than the null pair

This inversion (higher confidence on the null pair than the positive pair)
occurs because:
1. The statistic is mean log-return difference, not Sharpe difference
2. A0 has microscopically higher geometric growth than A1 (+0.001 annualized)
3. With 15,647 bars and deterministic subsampling, the method picks up this
   tiny signal as directionally consistent
4. The CI correctly reflects that this signal is economically meaningless

**The p_a_better from subsampling is NOT calibrated as a probability.**
A p of 0.97 on a null pair demonstrates that this value cannot be
interpreted as "97% probability A is better." The Politis-Romano-Wolf
procedure gives a one-sided test statistic, not a posterior probability.

The CI gate (median ci_lower > 0.0) correctly prevents false positives,
but also prevents all true positives — the support ratio is 0.00 for both
positive controls.

### 6.3 DSR: Irrelevant to Paired Comparison, But Revealing

The DSR is a per-strategy test, not a paired comparison. It asks: "Is this
strategy's Sharpe significantly above the expected max from random chance?"

**Finding**: VTREND_A0 with Sharpe 1.276 (annualized) fails DSR at ALL
trial levels, including N=27.

This happens because `compute_dsr` operates on per-bar (H4) returns:
- Per-bar SR = mean/std ≈ 0.027
- SR₀ for 27 trials, n=15,647 ≈ 0.016
- DSR statistic ≈ 1.36 (after kurtosis adjustment)
- Φ(1.36) ≈ 0.91 < 0.95 threshold

The high kurtosis of BTC H4 returns (~15-20) inflates the SR variance
correction, pushing the DSR below the 0.95 threshold. Note: the production
validation suite (`selection_bias.py`) uses a different calling convention
— it passes the annualized Sharpe to `deflated_sharpe()` with daily sample
count, which produces different (more lenient) results. The two DSR entry
points are not equivalent.

### 6.4 Permutation Tests: Not Applicable

The three permutation tests (EMA circular-shift, VDO random filter, ATR
block-shuffle) test individual VTREND components against randomized nulls.
They successfully proved that all three components contribute genuine alpha
(all p < 0.001, survive Bonferroni). But they cannot compare two strategies
against each other — they are component-level, not pair-level tests.

---

## 7. Is the Bootstrap Gate Too Permissive or Too Conservative?

**The bootstrap gate is correctly calibrated but utterly powerless.**

The gate's two conditions work as follows:
- `p >= 0.80`: requires 80% of bootstrap resamples to agree on direction.
  This is a reasonable directional bar. The strong positive pair PASSES this
  condition (p=0.82).
- `ci_lower > -0.01`: requires the 2.5th percentile of bootstrap Sharpe
  deltas to be above -0.01. With bootstrap CI width ~1.5 Sharpe units,
  this requires observed ΔSharpe >> 0.75.

**The CI condition is the binding constraint.** It demands near-zero
probability that A could be worse than B, which is a standard that cannot
be met with 7 years of H4 data and the autocorrelation/kurtosis structure
of BTC trend-following returns.

The gate is not "wrong" — it honestly reflects that we cannot statistically
distinguish these strategies at the conventional significance level. But it
makes the paired bootstrap useless as a decision tool: no achievable pair
in the repo will pass.

---

## 8. Is the Subsampling Gate Too Permissive or Too Conservative?

**The subsampling gate has the right structure but two problems:**

1. **p_a_better is miscalibrated.** It produces p=0.97 on a pair with
   ΔSharpe = -0.006. The subsampling p should not be interpreted as a
   probability or compared to thresholds designed for calibrated p-values.

2. **The CI condition (ci_lower > 0.0) is correctly conservative but
   cannot be satisfied.** Subsampling CIs span [-0.13, +0.63] even for
   ΔSharpe = +0.34. The support ratio is 0/3 = 0.00 for both positive
   controls.

The gate's three-part structure (p + CI + support) is sound in principle.
In practice, neither the p nor the CI delivers useful discrimination.

---

## 9. Root Cause: Fundamental Power Limitation

The failure of all methods on the strong positive control (ΔSharpe = +0.343)
is not a software bug. It reflects a mathematical reality:

**The sampling variance of the Sharpe ratio is too large relative to the
effect sizes available in this dataset.**

For a strategy with Sharpe S over T independent observations, the standard
error of the Sharpe estimator is approximately:

```
SE(Sharpe) ≈ sqrt((1 + S²/2) / T)
```

With S ≈ 1.3 and T_eff ≈ 500 (effective independent observations after
accounting for autocorrelation and intermittent exposure):

```
SE(Sharpe) ≈ sqrt((1 + 0.85) / 500) ≈ 0.061
```

For a paired comparison, the SE of the difference depends on the correlation
between the two strategies' returns. With ρ ≈ 0.53 (A0 vs VCUSUM):

```
SE(ΔSharpe) ≈ sqrt(SE_A² + SE_B² - 2ρ·SE_A·SE_B) ≈ 0.067
```

A z-test for ΔSharpe = +0.343 at SE = 0.067 gives z ≈ 5.1 — apparently
highly significant. But this assumes independent observations. The effective
T is uncertain and the block bootstrap honestly captures the autocorrelation
structure, resulting in much wider CIs than the naive z-test.

**The bootstrap CI width of ~1.5 implies the effective SE is ~0.38, not
0.067.** This corresponds to T_eff ≈ 15 — roughly 15 independent "macro
cycles" in 7 years of BTC data. With only ~15 independent draws, no
effect size below ~0.75 Sharpe units can be detected at 95% confidence.

---

## 10. Implications

### 10.1 For the Inference Stack

The current inference stack is **honest but powerless**:
- It correctly avoids false positives (negative control passes)
- It cannot detect true positives at any available effect size
- The gate thresholds are not the problem — the underlying data resolution is

### 10.2 For Strategy Comparison

**No pairwise strategy comparison on this dataset will pass the current
gates.** This applies to all pairs tested in this project (E-series, exit
family, VBREAK, VCUSUM, etc.). The paired bootstrap and subsampling gates
can only distinguish strategies whose Sharpe difference exceeds ~0.75,
and no such pair exists in the repo.

### 10.3 What the Stack CAN Do

The inference stack was used correctly for:
1. **Component tests**: EMA/VDO/ATR permutation tests work because they
   compare against a randomized null (reshuffled indicators), not another
   strategy. The null is dramatically different, giving huge effect sizes.
2. **DSR (validation suite entry point)**: When called via `deflated_sharpe`
   with annualized Sharpe and daily T, the DSR produces more lenient results
   than `compute_dsr` with H4 returns.
3. **Win-count analysis**: Reports 11/11b used win counts across 16
   timescales with binomial testing — a different (and more powerful)
   approach than single-timescale bootstrap CI.

### 10.4 What the Stack CANNOT Do

Distinguish between any two strategies in the repo at a single timescale
using paired block bootstrap or paired block subsampling with the current
gates.

---

## 11. Recommended Next Steps

1. **Do NOT relax the gates.** The CIs are wide for a real reason —
   there genuinely is not enough data to distinguish these strategies
   with statistical confidence.

2. **The win-count approach is more powerful.** Testing ΔSharpe > 0 at
   each of 16 timescales, then applying a binomial test on the count,
   aggregates weak signals across diverse conditions. This is what
   Reports 11/11b used successfully. It should be formalized as the
   primary paired comparison method.

3. **The paired bootstrap is useful for calibration, not gating.** Use it
   to estimate the magnitude and uncertainty of ΔSharpe, not as a pass/fail
   gate. Report the CI, don't gate on it.

4. **DSR entry points should be unified.** `compute_dsr` (per-bar) and
   `deflated_sharpe` (mixed annualized/daily) give different results for the
   same strategy. The validation suite's calling convention should be
   documented and chosen deliberately.

---

*Current inference stack evaluated. Both paired methods lack power to detect
any available effect size. Gates are honest but useless for strategy selection.*
