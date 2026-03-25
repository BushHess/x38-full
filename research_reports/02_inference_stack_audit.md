# Audit Report 02: Inference Stack Audit

**Date**: 2026-03-03
**Auditor**: Claude Opus 4.6
**Scope**: All statistical inference methods in the validation pipeline + research scripts

---

## 1. Method-by-Method Matrix

### 1.1 Paired Block Bootstrap

| Property | Value |
|----------|-------|
| **File** | `v10/research/bootstrap.py:160-219` |
| **Suite** | `validation/suites/bootstrap.py` (BootstrapSuite) |
| **Statistic** | `Sharpe(A) - Sharpe(B)` where Sharpe = `μ/σ·√2190`, ddof=0 |
| **Null hypothesis** | NOT formally stated. Implicitly H0: Sharpe(candidate) ≤ Sharpe(baseline) |
| **CI construction** | Percentile method on bootstrap distribution of deltas (2.5th/97.5th) |
| **p-value** | `p_a_better = fraction(bootstrap_deltas > 0)` — **NOT a p-value** (see §2.1) |
| **Assumptions** | (1) Circular block bootstrap is valid for the dependence structure, (2) Block size captures autocorrelation, (3) Percentile CI has correct coverage |
| **Output semantics** | CI for Sharpe *difference*, probability of observing positive delta under resampling |
| **Current role** | Soft gate in `decision.py:298-321` |
| **Suitable as primary gate?** | **NO** — `p_a_better` is not a calibrated p-value; the gate is a heuristic threshold |

### 1.2 Paired Block Subsampling

| Property | Value |
|----------|-------|
| **File** | `v10/research/subsampling.py:164-242` |
| **Suite** | `validation/suites/subsampling.py` (SubsamplingSuite) |
| **Statistic** | `E[log(r_A/r_B)]` — mean per-bar log-return difference, annualized via `expm1(2190·θ)` |
| **Null hypothesis** | `H0: annualized_excess_geometric_growth ≤ 0` (explicitly stated in result object) |
| **CI construction** | Subsampling quantile method: `θ̂ - q_{1-α/2}/√n` (Politis, Romano & Wolf 1999) |
| **p-value** | `p_value_one_sided = fraction(√b·(θ_b - θ_n) ≥ √n·θ_n)` — **proper subsampling p-value** |
| **Assumptions** | (1) Stationarity of log-return differences, (2) Block size b → ∞ but b/n → 0, (3) √b-consistent convergence of block means |
| **Output semantics** | CI for annualized excess geometric growth, genuine one-sided p-value |
| **Current role** | Soft gate in `decision.py` (via subsampling suite status, NOT directly in `evaluate_decision`) |
| **Suitable as primary gate?** | **YES, with caveats** — has formal null hypothesis, proper p-value construction, but tests growth not risk-adjusted return |

### 1.3 Deflated Sharpe Ratio (DSR)

| Property | Value |
|----------|-------|
| **File** | `research/lib/dsr.py:91-166` |
| **Suite** | `validation/suites/selection_bias.py` (SelectionBiasSuite, lines 129-148) |
| **Statistic** | `(SR_hat - SR_0) · √(n-1) / √(1 - skew·SR + ((kurt-1)/4)·SR²)` |
| **Null hypothesis** | `H0: observed Sharpe ≤ E[max SR under null]` (adjusts for multiple testing) |
| **p-value** | `Φ(DSR_statistic)` — proper CDF p-value under normal approximation |
| **Assumptions** | (1) Return stationarity, (2) Accurate estimation of skewness/kurtosis, (3) Gumbel approximation for max order statistic, (4) `num_trials` is known and correctly specified |
| **Output semantics** | Probability that observed SR exceeds what would arise from `num_trials` random strategies |
| **Current role** | Selection-bias advisory gate. Soft gate via "CAUTION" string detection in `decision.py:428-442` |
| **Suitable as primary gate?** | **NO** — answers a different question (is SR real?) not (is candidate better than baseline?). Single-strategy test, not paired. |

### 1.4 Permutation / Block-Shuffle Tests

| Property | Value |
|----------|-------|
| **Files** | `research/multiple_comparison.py` (10K perms), `research/component_analysis.py`, `research/true_wfo_compare.py` |
| **Suite** | **NOT IN VALIDATION PIPELINE** — research-only scripts |
| **Statistic** | Composite objective score = `2.5·CAGR - 0.60·MDD + 8.0·max(0,SR) + 5·max(0,min(PF,3)-1) + min(n/50,1)·5` |
| **Null hypothesis** | Component-specific: (1) EMA: H0=EMA-price alignment has no value (circular-shift), (2) VDO: H0=VDO filter = random filter at matched skip rate, (3) ATR: H0=local ATR-price alignment doesn't matter (block-shuffle) |
| **p-value** | `p = fraction(null_scores ≥ real_score)` — proper permutation p-value |
| **Assumptions** | (1) Block-shuffle/circular-shift creates valid null draws, (2) Test statistic (composite score) captures the effect of interest, (3) Blocks are large enough to preserve within-block dependence |
| **Output semantics** | Component-level significance: p-values for individual algorithm components |
| **Current role** | Research evidence only. Results cited in MEMORY.md (EMA p=0.0003, VDO p=0.031) |
| **Suitable as primary gate?** | **NO for paired candidate-vs-baseline** — tests component existence, not candidate superiority. Could be adapted for candidate-vs-baseline with different null. |

---

## 2. Current Production Gate Logic

### 2.1 Bootstrap Gate — `validation/suites/bootstrap.py:64-104` + `decision.py:298-321`

**Suite-level gate** (lines 99-104):
```python
p = float(gate.get("p_candidate_better") or 0.0)
ci_low = float(gate.get("ci_lower") or 0.0)
status = "pass" if p >= 0.80 and ci_low > -0.01 else "fail"
```

**Decision-level gate** (lines 307-308):
```python
passed = p >= policy.bootstrap_p_threshold and ci_low > policy.bootstrap_ci_lower_min
# Defaults: bootstrap_p_threshold=0.80, bootstrap_ci_lower_min=-0.01
```

#### 2.1.1 Is `p_candidate_better` a p-value?

**NO.** `p_a_better = fraction(bootstrap_deltas > 0)` is the proportion of bootstrap resamples where Sharpe(A) > Sharpe(B). This is:

- The bootstrap probability of candidate superiority under the **resampled** data distribution
- NOT a p-value testing H0: Sharpe(A) ≤ Sharpe(B)
- NOT comparable to α=0.05 or α=0.10 significance levels

A proper bootstrap p-value would center the null distribution at zero (e.g., by subtracting the observed delta from the bootstrap distribution). The current implementation does not do this.

**The name `p_candidate_better` is misleading** — it looks like a probability statement about the population parameter, but it's actually a property of the bootstrap distribution. For symmetric distributions, p_a_better ≈ 0.5 under H0, so the threshold of 0.80 is somewhat reasonable as a heuristic, but it has no formal statistical calibration.

#### 2.1.2 What are `ci_lower/ci_upper` a CI for?

The CI is for `Sharpe(A) - Sharpe(B)` — the Sharpe *difference*, annualized (ddof=0, 2190 bars/year).

This is a **percentile CI** (2.5th/97.5th of the bootstrap distribution), NOT a bias-corrected CI (BCa). Percentile CIs can be anti-conservative when the bootstrap distribution is skewed.

#### 2.1.3 Single scenario?

**YES.** The gate selects a SINGLE scenario for the pass/fail decision:

```python
# Priority: harsh → any harsh → first available
harsh_primary = next((row for row in rows
    if row.get("scenario") == "harsh"
    and row.get("block_size") == cfg.bootstrap_block_sizes[0]), None)
if harsh_primary is None:
    harsh_primary = next((row for row in rows if row.get("scenario") == "harsh"), None)
if harsh_primary is None and rows:
    harsh_primary = rows[0]
```

The gate uses ONLY the harsh scenario with the FIRST block size. All other scenarios and block sizes are computed but ignored for the pass/fail decision.

#### 2.1.4 Single block size?

**YES.** The gate prefers `bootstrap_block_sizes[0]` (default: 10 bars). Other block sizes (20, 40) are run but not used in the gate decision.

#### 2.1.5 Is the current gate a calibrated alpha-level test?

**NO.** The gate is a **heuristic** with two thresholds:
- `p_candidate_better ≥ 0.80` (not a p-value, not tied to any α)
- `ci_lower > -0.01` (arbitrary tolerance, not α-based)

There is no formal test at α=0.05 or any other significance level. The thresholds were chosen by engineering judgment, not statistical calibration.

#### 2.1.6 Equity curve alignment?

**WEAK.** `paired_block_bootstrap` (line 182):
```python
n = min(len(returns_a), len(returns_b))
returns_a = returns_a[:n]
returns_b = returns_b[:n]
```

This silently truncates the longer curve. It does NOT check that timestamps align. Two curves from different time periods could be compared without error. This is a **silent correctness hazard**.

Compare with subsampling (line 113-126 in `v10/research/subsampling.py`):
```python
if navs_a.size != navs_b.size:
    raise AlignmentError(...)
if has_ts_a and has_ts_b and ts_a != ts_b:
    raise AlignmentError("timestamps do not align exactly")
```

Subsampling has **strict alignment validation**; bootstrap has **none**.

### 2.2 Subsampling Gate — `validation/suites/subsampling.py:96-139`

The subsampling gate is more sophisticated:

```python
# Per block_size: pass if p_a_better ≥ p_threshold AND ci_lower > 0
support = (probs >= p_threshold) & (ci_lowers > ci_lower_threshold)
support_ratio = mean(support)

# Overall pass requires ALL THREE:
decision_pass = (
    median(probs) >= p_threshold          # default 0.80
    and median(ci_lowers) > ci_lower_threshold  # default 0.0
    and support_ratio >= support_ratio_threshold  # default 0.60
)
```

**Key differences from bootstrap gate:**
1. Uses **all block sizes** (median + support ratio), not just one
2. `p_a_better` here IS a proper subsampling p-value (see §1.2)
3. Requires stability across block sizes (support_ratio ≥ 0.60)
4. Has explicit thresholds with transparent defaults
5. Preferred scenario priority: harsh → base → smart

**However**, this gate is NOT wired into `evaluate_decision()` — it only sets the suite's status. The decision engine does not currently have a soft gate for subsampling like it does for bootstrap.

### 2.3 Selection-Bias (DSR) Gate — `validation/suites/selection_bias.py:129-218`

```python
for trials in [27, 54, 100, 200, 500, 700]:
    dsr, expected_max_sr, sr_std = _deflated_sharpe(...)
    passed = dsr > 0.95
```

The DSR gate:
- Tests DSR at 6 trial levels (27 to 700)
- Requires ALL to pass (dsr > 0.95) for "pass" status
- This is a **one-sided test** at α=0.05 (Φ(z) > 0.95 ⟹ z > 1.645)
- **BUT**: it's a single-strategy test, not paired candidate-vs-baseline
- Uses daily log-returns (not H4), which reduces n dramatically

**In `evaluate_decision()`** (lines 428-442): DSR is wired as a soft advisory that detects "CAUTION" in the risk_statement string. String-based gate detection is fragile.

### 2.4 Decision Engine Summary

The decision engine (`decision.py:53-474`) has this hierarchy:

| Gate | Severity | Source | What it tests |
|------|----------|--------|---------------|
| Data integrity | ERROR (abort) | data_integrity suite | Data quality |
| Invariants | ERROR (abort) | invariants suite | Logic correctness |
| Regression guard | ERROR (abort) | regression_guard suite | Metric stability |
| Lookahead | HARD | lookahead suite | No future leakage |
| Full harsh delta | HARD | backtest suite | Score tolerance |
| Holdout harsh delta | HARD | holdout suite | Out-of-sample score |
| WFO robustness | SOFT | wfo suite | Walk-forward win rate |
| Bootstrap | SOFT | bootstrap suite | Sharpe difference (heuristic) |
| Trade-level | SOFT | trade_level suite | Per-trade CI |
| Selection bias | SOFT | selection_bias suite | DSR advisory |

**Missing from decision engine:**
- Subsampling (computes gate but not wired to decision)
- Permutation tests (not in pipeline at all)

---

## 3. Unsafe Claims

### 3.1 "Bootstrap p_candidate_better is a p-value"

**UNSAFE.** `p_a_better = fraction(deltas > 0)` is NOT a p-value. It does not test H0: Sharpe(A) ≤ Sharpe(B). Under the null, the bootstrap distribution is centered at the OBSERVED delta (not zero), so this proportion reflects the resampled distribution's asymmetry, not statistical significance.

A proper bootstrap test would compute:
```python
centered_deltas = deltas - observed_delta  # center at null
p_value = fraction(centered_deltas >= observed_delta)  # one-sided
```

### 3.2 "The 0.80 threshold controls false positives at some known rate"

**UNSAFE.** The threshold p ≥ 0.80 has no formal connection to any significance level α. Prompt 01's simulation showed that actual Type I error for the bootstrap CI is ~2-3% (well below 5%), but this is a property of the CI, not of the p_a_better threshold.

### 3.3 "Bootstrap CI ensures candidate is better"

**UNSAFE.** `ci_lower > -0.01` allows a CI that includes 0 to pass. A Sharpe difference CI of [-0.009, +0.05] would pass, meaning we CANNOT reject that the candidate is worse. The -0.01 tolerance was chosen as "close enough to zero" but has no statistical basis.

### 3.4 "Bootstrap alignment is safe"

**UNSAFE.** `paired_block_bootstrap` silently truncates to `min(len_a, len_b)` without checking timestamps. If the engine produces curves of different lengths (e.g., one has warmup issues), the paired structure is violated.

### 3.5 "Permutation tests are distribution-free"

**PARTIALLY UNSAFE.** The claim "distribution-free" requires that the test statistic is pivotal under H0. The block-shuffle permutation in `multiple_comparison.py` preserves within-block dependence but:
- Circular-shift (EMA test): truly breaks only EMA-price alignment → valid if the shift is the ONLY null-relevant operation
- Block-shuffle (ATR test): block size choice affects the null distribution; too small destroys within-block vol clustering, too large reduces the number of permutations
- Random-filter (VDO test): this is NOT a permutation test — it's a randomization test with a specific calibrated skip rate. Valid for the specific question asked.

The claim is **mostly safe** for the EMA circular-shift test but **overstated** for the block-shuffle ATR test where the block size is a tuning parameter that affects the null.

---

## 4. Safe Claims

### 4.1 "Both bootstrap and subsampling CIs have correct coverage under heavy tails"

**SAFE.** Prompt 01's simulation (200 reps, Student-t df=3) confirmed:
- Bootstrap percentile CI: 94.0-95.0% coverage
- Subsampling CI: 96.0-96.5% coverage
- Both within Monte Carlo error of nominal 95%

*Caveat*: Coverage and Type I error were validated under a Student-t(3)
generator that lacks volatility clustering and has ~2× lower vol-of-vol
than real BTC 4H data (Report 03). These results confirm the methods'
mathematical correctness but should not be extrapolated as blanket
real-BTC guarantees. On real data, the bootstrap CI width on control
pairs (Report 18) is the binding constraint on power.

### 4.2 "Both methods control Type I error below 5%"

**SAFE.** Reproduced at 1.5-2.5% for both methods across block sizes [10, 20, 40].

*Caveat*: Same toy-generator limitation as §4.1 applies. See above.

### 4.3 "Subsampling tests a different hypothesis than bootstrap"

**SAFE.** Bootstrap tests `Sharpe(A) - Sharpe(B)`, subsampling tests `E[log(r_A/r_B)]` (geometric growth difference). These are genuinely different statistics that can disagree.

### 4.4 "DSR answers 'is the observed Sharpe genuine after multiple testing?'"

**SAFE.** The DSR implementation correctly follows Bailey & López de Prado (2014). It answers: "Given we tested N strategies, is this Sharpe significantly above what we'd expect by chance?"

### 4.5 "EMA permutation p=0.0003 survives Bonferroni correction"

**SAFE.** `multiple_comparison.py` applies Bonferroni, Holm, and BH corrections over 16 hypotheses. With K=16, Bonferroni threshold = 0.05/16 = 0.003125. p=0.0003 < 0.003125 → survives.

---

## 5. What Prompt 01 Does NOT Validate

### 5.1 Not tested: Bootstrap p_a_better as a decision statistic

Prompt 01 tested CI coverage and Type I error of the CI bounds. It did NOT test whether the threshold `p_a_better ≥ 0.80` has any useful operating characteristics (sensitivity, specificity, ROC) as a gate decision.

### 5.2 Not tested: The actual production gate composite

The production gate combines `p >= 0.80 AND ci_low > -0.01`. Prompt 01 tested these pieces separately but NOT the AND-composite. The -0.01 tolerance is arbitrary and was not simulated.

### 5.3 Not tested: Subsampling gate in the decision engine

Subsampling is computed but not wired into `evaluate_decision()`. Its impact on the PROMOTE/HOLD/REJECT outcome is untested.

### 5.4 Not tested: Single-scenario + single-block-size selection

The bootstrap gate uses ONLY harsh/block_size[0]. How often this disagrees with a multi-scenario or multi-block gate was not tested.

### 5.5 Not tested: Bootstrap alignment safety

The silent truncation in `paired_block_bootstrap` (line 182) was not tested for its impact when curves have different lengths or misaligned timestamps.

### 5.6 Not tested: DSR integration correctness

The selection_bias suite reimplements DSR inline (`_deflated_sharpe`, lines 35-51) separately from `research/lib/dsr.py`. Whether these two implementations agree was not verified.

### 5.7 Not tested: Power for realistic VTREND edge sizes

Prompt 01 found power ≈ 6.5% for a 5.6% annual edge. But the actual VTREND edge (CAGR ~14%, Sharpe ~0.54) may produce different power. The realistic-parameter power was not tested.

### 5.8 Not tested: Permutation tests in the validation pipeline

Permutation tests exist only in research scripts. Their integration into the validation pipeline was not assessed.

---

## 6. Recommended Next Experiments

### 6.1 IMMEDIATE — Calibrate bootstrap gate on realistic parameters

Run the Prompt 01 simulation framework with VTREND-realistic edge:
- edge = VTREND observed Sharpe difference (~0.54)
- Same heavy-tail generator
- Measure: (a) coverage of bootstrap CI, (b) power of `p_a_better ≥ 0.80` gate, (c) power of `ci_lower > 0` gate, (d) power of the AND-composite

**Why**: The 6.5% power result from Prompt 01 may not apply — it used a small edge. VTREND's edge is much larger. If power is high for VTREND's edge, the current gate may be acceptable despite its theoretical deficiencies.

### 6.2 IMMEDIATE — Wire subsampling into decision engine

Add a soft gate for subsampling in `evaluate_decision()` alongside bootstrap. Subsampling has:
- Proper p-value
- Multi-block-size stability gate
- Strict alignment validation

This would make the pipeline genuinely multi-method.

### 6.3 SHORT-TERM — Fix bootstrap alignment

Add timestamp alignment validation to `paired_block_bootstrap` matching the subsampling implementation. Either:
- Check `len(equity_a) == len(equity_b)` and raise if different
- Or validate timestamps align exactly

### 6.4 SHORT-TERM — Dual-DSR consistency check

Verify that `selection_bias.py:_deflated_sharpe()` (inline DSR) produces identical results to `research/lib/dsr.py:compute_dsr()` for the same inputs. If they diverge, consolidate to one implementation.

### 6.5 MEDIUM-TERM — Proper bootstrap p-value

Replace `p_a_better` with a proper centered bootstrap test:
```python
centered = deltas - observed_delta
p_value = float(np.mean(centered >= observed_delta))
```
And set the gate threshold to α=0.05 (or configure via `DecisionPolicy`).

### 6.6 MEDIUM-TERM — Integrate permutation test as hard gate

The permutation test infrastructure (`multiple_comparison.py`) already exists and produces calibrated p-values. Adding it as a suite would provide the only truly distribution-free test in the pipeline.

---

## Appendix: Files Read

| File | Lines | Purpose |
|------|-------|---------|
| `v10/research/bootstrap.py` | 250 | Circular block bootstrap + paired bootstrap |
| `v10/research/subsampling.py` | 285 | Paired block subsampling |
| `research/lib/dsr.py` | 167 | Deflated Sharpe Ratio |
| `research/lib/bootstrap.py` | 493 | VCBB (price path bootstrap, NOT used in validation) |
| `validation/suites/bootstrap.py` | 113 | BootstrapSuite |
| `validation/suites/subsampling.py` | 148 | SubsamplingSuite |
| `validation/suites/selection_bias.py` | 230 | SelectionBiasSuite (DSR + PBO proxy) |
| `validation/suites/base.py` | 66 | BaseSuite, SuiteContext, SuiteResult |
| `validation/suites/common.py` | 57 | ensure_backtest, scenario_costs |
| `validation/config.py` | 227 | ValidationConfig, resolve_suites |
| `validation/decision.py` | 475 | evaluate_decision, DecisionPolicy |
| `research/multiple_comparison.py` | ~530 | Bonferroni-corrected permutation tests |
| `research/component_analysis.py` | ~800 | Component permutation tests |
| `research/true_wfo_compare.py` | ~460 | VDO/EMA shuffle tests |

---

*Report generated 2026-03-03 by Claude Opus 4.6. No production code was modified.*
