# Report 19 — Same-Statistic Control Pair Audit

**Date**: 2026-03-03
**Artifacts**: `artifacts/19_same_statistic_control_pair_audit.py`,
`artifacts/19_same_statistic_control_pair_audit.json`
**Depends on**: Report 18 (current stack on control pairs)

---

## 1. Problem Statement

Report 18 compared bootstrap and subsampling but they tested **different
statistics**:

- **Bootstrap** tested: `Sharpe(A) - Sharpe(B)` (ratio of mean to std)
- **Subsampling** tested: `annualized excess geometric growth`
  (mean of differential log-returns, annualized)

This makes it impossible to determine whether behavioral differences
(e.g., subsampling p = 0.98 on the null pair vs bootstrap p = 0.47) are
due to the **method** or to the **statistic choice**.

This audit runs both methods on the **same statistic** to separate
method-family behavior from statistic choice.

---

## 2. Methods and Statistics Compared

### 2.1 Statistic A: Per-bar mean log-return difference

This is **subsampling's native statistic**. To make bootstrap test the same
quantity, we define an audit-only metric function:

```python
def mean_log_return(returns):
    return float(np.mean(np.log1p(returns)))
```

When used with `paired_block_bootstrap`, the delta becomes:

```
mean(log1p(rets_a[idx])) - mean(log1p(rets_b[idx]))
= mean(log_a[idx] - log_b[idx])
```

This is mathematically identical to subsampling's `observed_mean_log_diff`
computed on the same indices. **No production code is modified.**

### 2.2 Statistic B: Sharpe ratio

This is **bootstrap's production statistic**. Subsampling cannot compute
Sharpe natively (it has no pluggable metric function), so Statistic B is
bootstrap-only and serves as a reference for Report 18 comparison.

### 2.3 Configuration

Both methods: block sizes {10, 20, 40}, 2000 bootstrap replicates,
seed 1337, harsh cost (50bps RT), 2019-01-01 to 2026-02-20.

---

## 3. Pair-by-Pair Same-Statistic Results

### 3.1 Negative Control: VTREND_A0 vs VTREND_A1

**Observed**: ΔSharpe = -0.006, excess geo growth = +0.0007 (7 bps/year)

**Statistic A (mean log diff), block=20:**

| Method | observed Δ | p_a_better | CI (annualized) | CI width |
|---|---|---|---|---|
| **Bootstrap** | 3.2e-7 | **0.525** | [-0.045, +0.047] | 0.092 |
| **Subsampling** | 3.2e-7 | **0.965** | [-0.020, +0.012] | 0.031 |

**Block sensitivity (Statistic A):**

| Block | Boot p | Sub p | Boot CI_ann | Sub CI_ann |
|---|---|---|---|---|
| 10 | 0.522 | **0.980** | [-0.042, +0.044] | [+0.001, +0.001] |
| 20 | 0.525 | **0.965** | [-0.045, +0.047] | [-0.020, +0.012] |
| 40 | 0.544 | **0.939** | [-0.045, +0.047] | [-0.028, +0.028] |

**Statistic B (Sharpe, bootstrap only):**

| Block | p_a_better | CI |
|---|---|---|
| 10 | 0.474 | [-0.124, +0.107] |
| 20 | 0.473 | [-0.127, +0.112] |
| 40 | 0.499 | [-0.128, +0.111] |

**Finding**: On the same statistic (A), the two methods radically disagree
on p_a_better (0.52 vs 0.97) but agree on the conclusion (FAIL). Bootstrap
correctly gives p ≈ 0.5 (coin flip) for a null pair. Subsampling gives a
spuriously high p due to degeneracy (see §4). Both CIs span zero.

**Sensible?** Bootstrap: YES. Subsampling: p is NOT sensible, but gate
outcome is correct because the CI condition saves it.

---

### 3.2 Mid Positive Control: VTREND_A0 vs VBREAK

**Observed**: ΔSharpe = +0.098, excess geo growth = +0.129 (12.9%/year)

**Statistic A (mean log diff), block=20:**

| Method | observed Δ | p_a_better | CI (annualized) | CI width |
|---|---|---|---|---|
| **Bootstrap** | 5.55e-5 | **0.890** | [-0.071, +0.386] | 0.457 |
| **Subsampling** | 5.55e-5 | **0.905** | [-0.128, +0.418] | 0.546 |

**Block sensitivity (Statistic A):**

| Block | Boot p | Sub p | Boot CI_ann | Sub CI_ann |
|---|---|---|---|---|
| 10 | 0.901 | 0.925 | [-0.073, +0.374] | [-0.127, +0.431] |
| 20 | 0.890 | 0.905 | [-0.071, +0.386] | [-0.128, +0.418] |
| 40 | 0.884 | 0.895 | [-0.080, +0.383] | [-0.099, +0.414] |

**Statistic B (Sharpe, bootstrap only):**

| Block | p_a_better | CI |
|---|---|---|
| 10 | 0.644 | [-0.454, +0.638] |
| 20 | 0.644 | [-0.438, +0.651] |
| 40 | 0.648 | [-0.468, +0.668] |

**Finding**: On the same statistic (A), bootstrap and subsampling
**closely agree** on p_a_better (0.89 vs 0.91) and both agree the CI
spans zero. The methods are producing consistent inference when testing
the same quantity. Subsampling CI is ~20% wider than bootstrap CI.

**Sensible?** Both: yes. A ΔSharpe of +0.098 is legitimately hard to
detect. Both methods correctly indicate directional signal but insufficient
confidence. Neither should pass.

---

### 3.3 Strong Positive Control: VTREND_A0 vs VCUSUM

**Observed**: ΔSharpe = +0.343, excess geo growth = +0.219 (21.9%/year)

**Statistic A (mean log diff), block=20:**

| Method | observed Δ | p_a_better | CI (annualized) | CI width |
|---|---|---|---|---|
| **Bootstrap** | 9.06e-5 | **0.924** | [-0.069, +0.601] | 0.670 |
| **Subsampling** | 9.06e-5 | **0.930** | [-0.139, +0.616] | 0.755 |

**Block sensitivity (Statistic A):**

| Block | Boot p | Sub p | Boot CI_ann | Sub CI_ann |
|---|---|---|---|---|
| 10 | 0.929 | 0.937 | [-0.064, +0.587] | [-0.131, +0.625] |
| 20 | 0.924 | 0.930 | [-0.069, +0.601] | [-0.139, +0.616] |
| 40 | 0.927 | 0.926 | [-0.072, +0.596] | [-0.144, +0.625] |

**Statistic B (Sharpe, bootstrap only):**

| Block | p_a_better | CI |
|---|---|---|
| 10 | 0.818 | [-0.401, +1.072] |
| 20 | 0.798 | [-0.415, +1.127] |
| 40 | 0.811 | [-0.420, +1.095] |

**Finding**: On the same statistic (A), bootstrap and subsampling
**nearly perfectly agree** (p ≈ 0.93 for both). Both CIs span zero.
Block sensitivity is minimal for both methods.

**Sensible?** The directional signal is strong (93%) but the CI honestly
reflects that 7 years of data cannot exclude the possibility that A is
worse. This is a POWER issue, not a method issue.

---

## 4. Subsampling Block-10 Anomaly Analysis

### 4.1 Observation

Report 18 showed subsampling block=10 on the negative control producing:
- CI = [+0.0007, +0.0007] (width ≈ 0)
- p_a_better = 0.980

A point-estimate CI with near-certain p on a null pair.

### 4.2 Root Cause: Near-Degenerate Differential Series

The A0 vs A1 differential log-return series has:

| Property | Value |
|---|---|
| Total bars | 15,647 |
| Exact zeros (|diff| < 1e-15) | 82.6% |
| Non-zero bars | 2,730 (17.4%) |
| Full-sample mean | 3.20e-7 per bar |
| Unique block-10 means | **300** (out of 15,638 blocks) |

With 82.6% exact zeros, blocks of 10 consecutive bars have limited
variability. Of 15,638 overlapping blocks, only **300 unique mean values**
exist — massive discrete degeneracy.

### 4.3 Mechanism of CI Collapse

The subsampling CI is computed via:

```
root = sqrt(block_size) × (block_means - full_mean)
ci_lower = full_mean - quantile(root, 0.975) / sqrt(n)
ci_upper = full_mean - quantile(root, 0.025) / sqrt(n)
```

For block=10 on the negative control:

| Root property | Value |
|---|---|
| Std of root | 1.30e-3 |
| q2.5 | -1.01e-6 |
| q50 (median) | -1.01e-6 |
| q97.5 | -1.01e-6 |

**The 2.5th, 50th, and 97.5th quantiles are all identical** because the
root distribution has 300 unique values with massive ties. When q_low = q_high,
the CI collapses to a single point:

```
ci_width = (q_high - q_low) / sqrt(n) = 0 / 125 = 0
```

### 4.4 Mechanism of Inflated p

The test statistic is:

```
test_stat = sqrt(n) × full_mean = sqrt(15647) × 3.2e-7 = 4.0e-5
```

This is tiny in absolute terms, but most root values equal -1.01e-6 (a
value smaller than test_stat). Only 316 out of 15,638 root values exceed
test_stat, giving:

```
p_one_sided = 316/15638 = 0.020
p_a_better  = 1 - 0.020 = 0.980
```

The subsampling interprets the consistency of a 3.2e-7 per-bar mean
(0.07 bps/year excess return) as strong directional evidence because the
block-mean distribution has virtually no spread at the quantile level.

### 4.5 Scaling with Block Size

| Block | Unique means | q2.5 | q97.5 | CI width (raw) | p_a_better |
|---|---|---|---|---|---|
| 10 | 300 | -1.0e-6 | -1.0e-6 | **9.0e-18** | **0.980** |
| 20 | 309 | -6.1e-4 | +1.2e-3 | 1.4e-5 | 0.965 |
| 40 | 312 | -1.6e-3 | +1.6e-3 | 2.5e-5 | 0.939 |

Larger blocks capture more non-zero bars, creating wider root
distributions and less extreme p-values. The progression from p=0.98
to p=0.94 as block size increases is consistent with reduced degeneracy.

### 4.6 Diagnosis

**This is NOT a code bug.** It is an expected mathematical consequence
of applying overlapping-block subsampling to a series that is >80%
exact zeros. The Politis-Romano-Wolf (1999) theoretical guarantees
assume a smooth distribution of block means, which does not hold when the
underlying series is near-degenerate.

**The bootstrap does NOT have this problem** because circular block
resampling creates genuine variability in the aggregate statistic: each
resample randomly includes different sets of the 2,730 non-zero bars,
producing a non-degenerate distribution of bootstrap deltas
(p = 0.52, correctly near 0.5).

### 4.7 Positive Controls Are Not Affected

For A0 vs VBREAK (66.7% zeros) and A0 vs VCUSUM (57.3% zeros), the
degeneracy is much less severe:

| Pair | Zero rate | Unique block-10 means | Block-10 CI width (ann) |
|---|---|---|---|
| A0 vs A1 | 82.6% | 300 | **0.0000** |
| A0 vs VBREAK | 66.7% | 5,262 | 0.558 |
| A0 vs VCUSUM | 57.3% | 7,030 | 0.756 |

The positive controls have enough non-zero bars to produce a smooth
block-mean distribution. The anomaly is specific to near-identical pairs.

---

## 5. Production vs Audit Comparison

### 5.1 What Production Does

| Component | Production behavior |
|---|---|
| Bootstrap statistic | Sharpe ratio |
| Bootstrap gate | p ≥ 0.80 AND ci_lower > -0.01 |
| Subsampling statistic | Annualized excess geometric growth |
| Subsampling gate | median_p ≥ 0.80 AND median_ci > 0.0 AND support ≥ 0.60 |

Production compares two methods that test **different quantities**. The
gate thresholds are tuned to their respective statistics but the methods
cannot be compared against each other because they answer different questions.

### 5.2 What This Audit Reveals

When both methods test the **same statistic** (mean log-return difference):

| Pair | Control type | Boot p | Sub p | Boot CI spans 0? | Sub CI spans 0? |
|---|---|---|---|---|---|
| A0 vs A1 | Negative | **0.525** | **0.965** | Yes | Yes |
| A0 vs VBREAK | Mid positive | **0.890** | **0.905** | Yes | Yes |
| A0 vs VCUSUM | Strong positive | **0.924** | **0.930** | Yes | Yes |

**Key observations:**

1. **On non-degenerate pairs (mid & strong), both methods agree closely**
   (p differs by <2 percentage points). The method choice barely matters
   when the statistic is the same.

2. **On the degenerate pair (negative), the methods diverge** — bootstrap
   gives p = 0.52 (correct), subsampling gives p = 0.97 (inflated by
   degeneracy). This is a method-level flaw in subsampling for this data
   type, not a statistic issue.

3. **Both CIs span zero for ALL pairs, regardless of method.** Neither
   method has the statistical power to produce a CI that excludes zero on
   any available pair.

### 5.3 Statistic Choice Matters More Than Method Choice

Switching from Statistic A (geo growth) to Statistic B (Sharpe) on
bootstrap dramatically changes the output:

| Pair | Boot p (geo growth) | Boot p (Sharpe) | Δp |
|---|---|---|---|
| A0 vs A1 | 0.525 | 0.474 | -0.051 |
| A0 vs VBREAK | 0.890 | 0.644 | **-0.246** |
| A0 vs VCUSUM | 0.924 | 0.818 | **-0.106** |

**Sharpe reduces p_a_better by 10-25 percentage points** relative to
geometric growth on the same data with the same resampling. This is because
Sharpe = mean/std introduces variance-of-variance noise: resampled blocks
that include extreme bars inflate std, depressing resampled Sharpe. Geometric
growth (mean only) is immune to this effect.

The CI widths confirm this:

| Pair | Boot CI width (geo growth, ann) | Boot CI width (Sharpe) |
|---|---|---|
| A0 vs A1 | 0.092 | 0.231 |
| A0 vs VBREAK | 0.457 | 1.093 |
| A0 vs VCUSUM | 0.670 | 1.473 |

**Sharpe CIs are 2-2.5× wider than geometric growth CIs.** The additional
variance from the denominator (std) makes Sharpe comparison fundamentally
harder than geometric growth comparison.

---

## 6. Which Conclusions Survive

### From Report 18

| Report 18 conclusion | Status |
|---|---|
| "Bootstrap correctly rejects negative control" | **SURVIVES** — p = 0.47 (Sharpe) or 0.52 (geo), both correct |
| "Subsampling correctly rejects negative control" | **SURVIVES on gate outcome, FAILS on p calibration** — p = 0.97 is a degeneracy artifact, not a meaningful probability |
| "Both methods lack power on strong positive" | **SURVIVES** — confirmed on same statistic (CIs span zero) |
| "Bootstrap CIs are enormously wide" | **PARTIALLY SURVIVES** — true for Sharpe (width 1.5), but geo growth CI is 2.5× narrower (width 0.67). The width is partly statistic-dependent |
| "The two methods give very different results" | **FAILS** — on the same statistic, they give nearly identical results for non-degenerate pairs |

### New conclusions from this audit

| New conclusion | Evidence |
|---|---|
| **Statistic choice, not method choice, drives most of the observed differences in Report 18** | Boot p(geo)=0.92 vs Boot p(Sharpe)=0.82 for same pair, same resampling |
| **Subsampling p is NOT calibrated on near-identical pairs** | p = 0.97 on a null pair with ΔSharpe = -0.006 |
| **Bootstrap p IS correctly calibrated on same data** | p = 0.52 on same null pair |
| **Both methods agree closely on non-degenerate data** | p differs by <2pp on mid and strong controls |
| **The block-10 CI collapse is a degeneracy artifact, not a bug** | Expected when >80% of differential returns are exact zeros |

---

## 7. Which Conclusions Fail

| Failed conclusion | Why |
|---|---|
| "Subsampling and bootstrap disagree on the negative control" (Report 18 implied) | They disagree because one tests Sharpe and the other tests geo growth. On the same statistic with non-degenerate data, they agree. On degenerate data, subsampling p is inflated regardless of statistic. |
| "The bootstrap is too conservative" (Report 18 implied for CIs) | The bootstrap geo-growth CI is [-0.07, +0.60] — much narrower than the Sharpe CI of [-0.40, +1.07]. The "excessive width" is a property of the Sharpe statistic, not of the bootstrap method. |
| "Current inference stack is fundamentally different from the subsampling alternative" | On the same statistic, they produce nearly identical inference for non-degenerate pairs. The apparent disagreement in Report 18 was driven by testing different statistics. |

---

## 8. Recommended Next Step

The natural experiment is now clear:

**Run bootstrap on geometric growth (Statistic A) instead of Sharpe
(Statistic B) through the production gate.**

If the production gate used `mean_log_return` as the metric:

| Pair | p_a_better | ci_lower (ann) | Gate (p≥0.80, ci>0) |
|---|---|---|---|
| A0 vs A1 (null) | 0.525 | -0.045 | **FAIL** ✓ |
| A0 vs VBREAK (mid) | 0.890 | -0.071 | **FAIL** (CI) |
| A0 vs VCUSUM (strong) | 0.924 | -0.069 | **FAIL** (CI) |

Even with the narrower geo-growth CI, the strong positive still fails
because ci_lower = -0.069 < 0. The fundamental power limitation from
Report 18 holds: **7 years of H4 data with intermittent exposure cannot
exclude the possibility that A is worse than B for any available pair.**

However, the geo-growth bootstrap produces CIs that are 2.5× narrower
and p-values that are 10-25pp higher. If future pairs have larger effect
sizes (e.g., ΔSharpe > 0.5 or exposure agreement > 80%), the geo-growth
bootstrap would reach significance before the Sharpe bootstrap.

**Concrete recommendation**: The next report should formalize the
multi-timescale win-count protocol (16 timescales × binomial test) as an
alternative to single-timescale CI-based gates. Reports 11/11b demonstrated
this approach works where bootstrap/subsampling fails.

---

*Same-statistic audit complete. Method disagreement from Report 18 was
primarily a statistic-choice artifact. On the same statistic, bootstrap
and subsampling agree within 2 percentage points on non-degenerate data.
Subsampling p is miscalibrated on degenerate pairs (>80% exact zeros).
Power limitation holds regardless of method or statistic choice.*
